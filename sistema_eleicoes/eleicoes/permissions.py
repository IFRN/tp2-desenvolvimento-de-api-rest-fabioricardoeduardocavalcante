from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class IsEleitorApto(permissions.BasePermission):
    def has_permission(self, request, view):
        # Verificação específica para votação
        token = request.data.get('token_eleitor')
        eleicao_id = request.data.get('eleicao_id')
        
        if not token or not eleicao_id:
            return False
        
        # Validação adicional será feita no serializer
        return True