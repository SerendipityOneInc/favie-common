import httpx
from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

app = FastAPI()


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        authorization: str = request.headers.get("authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header missing")

        user_info = await self.get_user_info(authorization)

        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid token or user not found")

        # 将用户信息放入请求头
        request.state.user_info = user_info

        response = await call_next(request)
        return response

    async def get_user_info(self, token: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://user-interface.favie.svc.cluster.local/auth/verify", headers={"Authorization": token}
            )
            if response.status_code == 200:
                return response.json()
            return None
