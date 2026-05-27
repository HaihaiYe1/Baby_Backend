import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.models import User
from app.schemas import UserCreate, UserLogin, UserUpdate, ChangePasswordRequest
from app.crud import create_user, authenticate_user, get_user_by_email
from app.utils.database import get_db
from app.utils.security import hash_password, verify_password, create_access_token, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    """注册用户"""
    try:
        result = create_user(db, user)
        return {"message": "User created successfully", "user": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    stored_user = authenticate_user(db, user.email, user.password)
    if not stored_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": stored_user.email})
    logger.info(f"用户登录成功: {stored_user.email}")
    
    return {
        "token": token,
        "username": stored_user.username,
        "email": stored_user.email,
        "id": stored_user.id
    }


@router.get("/me")
def get_current_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户信息"""
    return {
        "email": current_user.email,
        "username": current_user.username,
        "id": current_user.id
    }


@router.put("/update-user")
async def update_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """修改用户名"""
    # 通过current_user获取用户，无需email字段
    db_user = db.query(User).filter(User.id == current_user.id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 更新用户名
    if user_update.username:
        # 检查用户名是否已被使用
        existing = db.query(User).filter(
            User.username == user_update.username,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        db_user.username = user_update.username

    db.commit()
    db.refresh(db_user)
    return {"message": "Username updated successfully", "username": db_user.username}


@router.put("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """修改密码"""
    # 验证旧密码
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    # 更新密码
    current_user.hashed_password = hash_password(request.new_password)
    db.commit()
    
    logger.info(f"用户修改密码成功: {current_user.email}")
    return {"message": "Password updated successfully"}
