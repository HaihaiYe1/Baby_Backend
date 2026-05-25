import asyncio
import base64
import io
import struct
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum


class AudioFormat(str, Enum):
    """音频格式"""
    PCM = "pcm"
    WAV = "wav"
    OPUS = "opus"
    AAC = "aac"


@dataclass
class AudioConfig:
    """音频配置"""
    sample_rate: int = 16000
    channels: int = 1
    bits_per_sample: int = 16
    format: AudioFormat = AudioFormat.PCM
    chunk_size: int = 1024


@dataclass
class AudioChunk:
    """音频数据块"""
    data: bytes
    timestamp: float
    device_id: int
    sequence: int
    sample_rate: int
    channels: int


class AudioBuffer:
    """音频缓冲区"""
    
    def __init__(self, max_size: int = 100):
        """
        初始化音频缓冲区
        
        Args:
            max_size: 最大缓冲块数
        """
        self.max_size = max_size
        self.chunks: List[AudioChunk] = []
        self.lock = asyncio.Lock()
    
    async def push(self, chunk: AudioChunk):
        """添加音频块"""
        async with self.lock:
            self.chunks.append(chunk)
            if len(self.chunks) > self.max_size:
                self.chunks.pop(0)
    
    async def pop(self) -> Optional[AudioChunk]:
        """取出音频块"""
        async with self.lock:
            if self.chunks:
                return self.chunks.pop(0)
            return None
    
    async def get_latest(self, count: int = 1) -> List[AudioChunk]:
        """获取最新的音频块"""
        async with self.lock:
            return self.chunks[-count:] if self.chunks else []
    
    def clear(self):
        """清空缓冲区"""
        self.chunks.clear()
    
    def size(self) -> int:
        """获取缓冲区大小"""
        return len(self.chunks)


class AudioProcessor:
    """音频处理器"""
    
    def __init__(self, config: Optional[AudioConfig] = None):
        """
        初始化音频处理器
        
        Args:
            config: 音频配置
        """
        self.config = config or AudioConfig()
        self.is_processing = False
        self._callbacks: List[Callable] = []
    
    def register_callback(self, callback: Callable):
        """注册音频处理回调"""
        self._callbacks.append(callback)
    
    def encode_audio(self, audio_data: bytes) -> str:
        """
        编码音频数据为Base64
        
        Args:
            audio_data: 原始音频数据
            
        Returns:
            Base64编码的字符串
        """
        return base64.b64encode(audio_data).decode('utf-8')
    
    def decode_audio(self, encoded_data: str) -> bytes:
        """
        解码Base64音频数据
        
        Args:
            encoded_data: Base64编码的字符串
            
        Returns:
            原始音频数据
        """
        return base64.b64decode(encoded_data)
    
    def create_wav_header(self, data_size: int) -> bytes:
        """
        创建WAV文件头
        
        Args:
            data_size: 音频数据大小
            
        Returns:
            WAV文件头
        """
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',                    # ChunkID
            data_size + 36,             # ChunkSize
            b'WAVE',                    # Format
            b'fmt ',                    # Subchunk1ID
            16,                         # Subchunk1Size
            1,                          # AudioFormat (PCM)
            self.config.channels,       # NumChannels
            self.config.sample_rate,    # SampleRate
            self.config.sample_rate * self.config.channels * self.config.bits_per_sample // 8,  # ByteRate
            self.config.channels * self.config.bits_per_sample // 8,  # BlockAlign
            self.config.bits_per_sample,# BitsPerSample
            b'data',                    # Subchunk2ID
            data_size                   # Subchunk2Size
        )
        return header
    
    def pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """
        将PCM数据转换为WAV格式
        
        Args:
            pcm_data: PCM音频数据
            
        Returns:
            WAV格式音频数据
        """
        header = self.create_wav_header(len(pcm_data))
        return header + pcm_data
    
    def resample(
        self,
        audio_data: bytes,
        source_rate: int,
        target_rate: int
    ) -> bytes:
        """
        重采样音频数据
        
        Args:
            audio_data: 原始音频数据
            source_rate: 源采样率
            target_rate: 目标采样率
            
        Returns:
            重采样后的音频数据
        """
        if source_rate == target_rate:
            return audio_data
        
        # 简单的线性插值重采样
        # 注意：生产环境应使用专业的音频处理库
        ratio = source_rate / target_rate
        source_samples = len(audio_data) // 2  # 假设16位采样
        target_samples = int(source_samples / ratio)
        
        result = bytearray(target_samples * 2)
        
        for i in range(target_samples):
            source_pos = i * ratio
            source_idx = int(source_pos)
            fraction = source_pos - source_idx
            
            if source_idx + 1 < source_samples:
                # 线性插值
                sample1 = struct.unpack_from('<h', audio_data, source_idx * 2)[0]
                sample2 = struct.unpack_from('<h', audio_data, (source_idx + 1) * 2)[0]
                interpolated = int(sample1 + fraction * (sample2 - sample1))
                struct.pack_into('<h', result, i * 2, interpolated)
            elif source_idx < source_samples:
                struct.pack_into('<h', result, i * 2, 
                    struct.unpack_from('<h', audio_data, source_idx * 2)[0])
        
        return bytes(result)
    
    def mix_audio(self, audio1: bytes, audio2: bytes) -> bytes:
        """
        混合两路音频
        
        Args:
            audio1: 音频1
            audio2: 音频2
            
        Returns:
            混合后的音频
        """
        # 确保长度一致
        min_len = min(len(audio1), len(audio2))
        audio1 = audio1[:min_len]
        audio2 = audio2[:min_len]
        
        result = bytearray(min_len)
        
        for i in range(0, min_len, 2):
            sample1 = struct.unpack_from('<h', audio1, i)[0]
            sample2 = struct.unpack_from('<h', audio2, i)[0]
            
            # 混合并防止溢出
            mixed = max(-32768, min(32767, (sample1 + sample2) // 2))
            struct.pack_into('<h', result, i, mixed)
        
        return bytes(result)
    
    def apply_noise_reduction(self, audio_data: bytes) -> bytes:
        """
        简单的噪声抑制
        
        Args:
            audio_data: 原始音频数据
            
        Returns:
            处理后的音频数据
        """
        # 简单的噪声门限
        threshold = 500  # 阈值
        result = bytearray(len(audio_data))
        
        for i in range(0, len(audio_data), 2):
            sample = struct.unpack_from('<h', audio_data, i)[0]
            
            if abs(sample) < threshold:
                sample = 0
            
            struct.pack_into('<h', result, i, sample)
        
        return bytes(result)
    
    async def process_chunk(self, chunk: AudioChunk) -> AudioChunk:
        """
        处理音频块
        
        Args:
            chunk: 原始音频块
            
        Returns:
            处理后的音频块
        """
        # 应用噪声抑制
        processed_data = self.apply_noise_reduction(chunk.data)
        
        # 如果采样率不同，进行重采样
        if chunk.sample_rate != self.config.sample_rate:
            processed_data = self.resample(
                processed_data,
                chunk.sample_rate,
                self.config.sample_rate
            )
        
        # 创建新的音频块
        processed_chunk = AudioChunk(
            data=processed_data,
            timestamp=chunk.timestamp,
            device_id=chunk.device_id,
            sequence=chunk.sequence,
            sample_rate=self.config.sample_rate,
            channels=chunk.channels
        )
        
        # 调用回调
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(processed_chunk)
                else:
                    callback(processed_chunk)
            except Exception as e:
                print(f"音频处理回调失败: {e}")
        
        return processed_chunk


class AudioService:
    """音频服务"""
    
    def __init__(self):
        """初始化音频服务"""
        self.processor = AudioProcessor()
        self.buffers: Dict[int, AudioBuffer] = {}  # 设备ID -> 缓冲区
        self.is_streaming: Dict[int, bool] = {}  # 设备ID -> 是否正在流式传输
        self.sequence_counters: Dict[int, int] = {}  # 设备ID -> 序列号
        
    def get_or_create_buffer(self, device_id: int) -> AudioBuffer:
        """获取或创建设备的音频缓冲区"""
        if device_id not in self.buffers:
            self.buffers[device_id] = AudioBuffer()
        return self.buffers[device_id]
    
    def get_next_sequence(self, device_id: int) -> int:
        """获取下一个序列号"""
        if device_id not in self.sequence_counters:
            self.sequence_counters[device_id] = 0
        self.sequence_counters[device_id] += 1
        return self.sequence_counters[device_id]
    
    async def process_audio_data(
        self,
        device_id: int,
        audio_data: str,
        sample_rate: int = 16000,
        channels: int = 1
    ) -> AudioChunk:
        """
        处理接收到的音频数据
        
        Args:
            device_id: 设备ID
            audio_data: Base64编码的音频数据
            sample_rate: 采样率
            channels: 声道数
            
        Returns:
            处理后的音频块
        """
        # 解码音频数据
        decoded_data = self.processor.decode_audio(audio_data)
        
        # 创建音频块
        chunk = AudioChunk(
            data=decoded_data,
            timestamp=time.time(),
            device_id=device_id,
            sequence=self.get_next_sequence(device_id),
            sample_rate=sample_rate,
            channels=channels
        )
        
        # 处理音频块
        processed_chunk = await self.processor.process_chunk(chunk)
        
        # 添加到缓冲区
        buffer = self.get_or_create_buffer(device_id)
        await buffer.push(processed_chunk)
        
        return processed_chunk
    
    async def get_audio_stream(
        self,
        device_id: int,
        chunk_count: int = 1
    ) -> List[Dict[str, Any]]:
        """
        获取音频流数据
        
        Args:
            device_id: 设备ID
            chunk_count: 获取的块数
            
        Returns:
            音频数据列表
        """
        buffer = self.get_or_create_buffer(device_id)
        chunks = await buffer.get_latest(chunk_count)
        
        return [
            {
                "data": self.processor.encode_audio(chunk.data),
                "timestamp": chunk.timestamp,
                "sequence": chunk.sequence,
                "sample_rate": chunk.sample_rate,
                "channels": chunk.channels
            }
            for chunk in chunks
        ]
    
    def start_streaming(self, device_id: int):
        """开始流式传输"""
        self.is_streaming[device_id] = True
    
    def stop_streaming(self, device_id: int):
        """停止流式传输"""
        self.is_streaming[device_id] = False
    
    def is_device_streaming(self, device_id: int) -> bool:
        """检查设备是否正在流式传输"""
        return self.is_streaming.get(device_id, False)
    
    def clear_buffer(self, device_id: int):
        """清空设备的音频缓冲区"""
        if device_id in self.buffers:
            self.buffers[device_id].clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取音频服务统计"""
        return {
            "active_devices": len(self.buffers),
            "streaming_devices": sum(1 for v in self.is_streaming.values() if v),
            "buffer_sizes": {
                device_id: buffer.size()
                for device_id, buffer in self.buffers.items()
            }
        }


# 全局音频服务实例
audio_service = AudioService()
