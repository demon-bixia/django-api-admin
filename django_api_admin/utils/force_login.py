from rest_framework_simplejwt.tokens import RefreshToken


def force_login(client, user):
    """
    force login the user.
    """
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
