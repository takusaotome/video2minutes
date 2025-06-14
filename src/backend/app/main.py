from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import os
import time
from typing import Dict

from app.config import settings
from app.models import MinutesTask
from app.api.endpoints import minutes
from app.utils.logger import setup_logging, get_logger
from app.services.task_queue import initialize_task_queue, shutdown_task_queue


# ロギング初期化
logger = setup_logging(
    log_level=settings.log_level,
    log_dir=settings.log_dir,
    app_name="video2minutes"
)

# グローバルタスクストア（本番環境ではRedisやDBを使用）
tasks_store: Dict[str, MinutesTask] = {}


def create_app() -> FastAPI:
    """FastAPIアプリケーションを作成"""
    
    app = FastAPI(
        title="Video2Minutes API",
        description="動画から議事録を生成するAPIサービス",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS設定
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # リクエストロギングミドルウェア
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        # リクエスト情報をログ
        logger.info(
            f"リクエスト開始: {request.method} {request.url}",
            extra={
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        try:
            response = await call_next(request)
            
            # レスポンス時間を計算
            process_time = time.time() - start_time
            
            # レスポンス情報をログ
            logger.info(
                f"リクエスト完了: {request.method} {request.url} - {response.status_code} ({process_time:.3f}s)",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "client_ip": request.client.host if request.client else None
                }
            )
            
            return response
            
        except Exception as exc:
            process_time = time.time() - start_time
            logger.error(
                f"リクエストエラー: {request.method} {request.url} - {type(exc).__name__}: {str(exc)} ({process_time:.3f}s)",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "process_time": process_time,
                    "client_ip": request.client.host if request.client else None
                }
            )
            raise
    
    # ルーターを追加
    app.include_router(
        minutes.router,
        prefix="/api/v1/minutes",
        tags=["minutes"]
    )
    
    # 必要なディレクトリを作成
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.temp_dir, exist_ok=True)
    
    logger.info(f"アプリケーション初期化完了")
    logger.info(f"アップロードディレクトリ: {settings.upload_dir}")
    logger.info(f"一時ディレクトリ: {settings.temp_dir}")
    logger.info(f"デバッグモード: {settings.debug}")
    logger.info(f"CORS許可オリジン: {settings.cors_origins}")
    
    # アプリケーション起動・停止イベント
    @app.on_event("startup")
    async def startup_event():
        logger.info("アプリケーション起動: タスクキュー初期化開始")
        await initialize_task_queue()
        logger.info("タスクキュー初期化完了")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("アプリケーション停止: タスクキュー停止開始")
        await shutdown_task_queue()
        logger.info("タスクキュー停止完了")
    
    @app.get("/")
    async def root():
        return {"message": "Video2Minutes API", "version": "1.0.0"}
    
    @app.get("/health")
    async def health_check():
        from app.services.task_queue import get_task_queue
        queue = get_task_queue()
        queue_status = queue.get_queue_status()
        
        return {
            "status": "healthy", 
            "tasks_count": len(tasks_store),
            "queue": queue_status
        }
    
    # グローバル例外ハンドラー
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(
            f"未処理例外: {type(exc).__name__}: {str(exc)}",
            extra={
                "method": request.method,
                "url": str(request.url),
                "error": str(exc),
                "error_type": type(exc).__name__,
                "client_ip": request.client.host if request.client else None
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "予期しないエラーが発生しました。",
                "detail": str(exc) if settings.debug else None
            }
        )
    
    return app


# アプリケーションインスタンス
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )