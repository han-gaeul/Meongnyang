from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path("auth/signup", views.SignupView.as_view(), name="signup"),
    path("auth/login", TokenObtainPairView.as_view(), name="login"),
    path("auth/token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout", views.LogoutView.as_view(), name="logout"),
    path("auth/social/<str:provider>", views.SocialLoginView.as_view(), name="social-login"),
    path("auth/identity/verify", views.IdentityVerifyView.as_view(), name="identity-verify"),
    path("me", views.MeView.as_view(), name="me"),
    path("users/<int:pk>", views.UserDetailView.as_view(), name="user-detail"),
    path("users/<int:pk>/follow", views.FollowView.as_view(), name="user-follow"),
    path("users/<int:pk>/block", views.BlockView.as_view(), name="user-block"),
]
