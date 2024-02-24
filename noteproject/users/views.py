import jwt

from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from .serializers import UserSerializer

from config.settings import SECRET_KEY

class RegisterAPIView(APIView):
    def post(self,request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            token = TokenObtainPairSerializer.get_token(user)
            refresh_token = str(token)
            access_token = str(token.access_token)
            res = Response(
                {
                    "user":serializer.data,
                    "message":"register success",
                    "token":{
                        "access":access_token,
                        "refrest":refresh_token,
                    },
                },
                status = status.HTTP_200_OK,
            )

            # 쿠키에 토큰 저장 => JS로 쿠키 조회 불가능 => XSS 로부터는 안전 but CSRF 취약해짐

            res.set_cookie("access",access_token,httponly=True)
            res.set_cookie("refresh",refresh_token,httponly=True)
            return res
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    
class AuthAPIView(APIView):
    # 유저 정보 확인용
    def get(self,request):
        try:
            # access 토큰을 decode 하여 유저 id 추출
            access = request.COOKIES['access']
            payload = jwt.decode(access,SECRET_KEY,algorithms=['HS256'])
            pk = payload.get('user_id')
            user = get_object_or_404(User,pk=pk)
            serializer = UserSerializer(instance=user)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
        except(jwt.exceptions.ExpireSignatureError):
            # 토큰 만료시 토큰 갱신
            data = {'refresh':request.COOKIES.get('refresh',None)}
            serializer = TokenRefreshSerializer(data=data)
            if serializer.is_valid(raise_exception=True):
                access = serializer.data.get('access',None)
                refresh = serializer.data.get('refresh',None)
                payload = jwt.decode(access,SECRET_KEY,algorithms=['HS256'])
                pk = payload.get('user_id')
                user = get_object_or_404(User,pk=pk)
                serializer = UserSerializer(instance=user)
                res = Response(serializer.data,status=status.HTTP_200_OK)
                res.set_cookie('access',access)
                res.set_cookie('refresh',refresh)
                return res
            raise jwt.exceptions.InvalidTokenError
        
        except(jwt.exceptions.InvalidTokenError):
            # 토큰이 사용 불가시
            return Response(status=status.HTTP_400_BAD_REQUEST)
    
    # 로그인용
    def post(self, request):
    	# 유저 인증
        user = authenticate(
            email=request.data.get("email"), password=request.data.get("password")
        )
        # 이미 회원가입 된 유저일 때
        if user is not None:
            serializer = UserSerializer(user)
            token = TokenObtainPairSerializer.get_token(user)
            refresh_token = str(token)
            access_token = str(token.access_token)
            res = Response(
                {
                    "user": serializer.data,
                    "message": "login success",
                    "token": {
                        "access": access_token,
                        "refresh": refresh_token,
                    },
                },
                status=status.HTTP_200_OK,
            )
            res.set_cookie("access", access_token, httponly=True)
            res.set_cookie("refresh", refresh_token, httponly=True)
            return res
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    # 로그아웃용
    def delete(self, request):
        # 쿠키에 있는 토큰 삭제
        response = Response({
            "message": "Logout success"
            }, status=status.HTTP_202_ACCEPTED)
        response.delete_cookie("access")
        response.delete_cookie("refresh")
        return response