import qrcode
import secrets
import hashlib
import base64
from io import BytesIO
from datetime import datetime

def gerar_token_comprovante():
    """
    Gera um token aleatório seguro para o comprovante de voto
    """
    return secrets.token_urlsafe(32)

def gerar_hash_token(token):
    """
    Gera hash do token para armazenamento no banco (irreversível)
    """
    return hashlib.sha256(token.encode()).hexdigest()

def gerar_qrcode_comprovante(token, dados_voto):
    """
    Gera QR Code com os dados do comprovante
    O token NÃO fica armazenado no banco, apenas no QR Code entregue ao eleitor
    """
    # Dados que vão no QR Code
    qr_data = {
        'token': token,
        'data_hora': dados_voto['data_hora'].isoformat(),
        'candidato': dados_voto['candidato_nome'],
        'eleicao': dados_voto['eleicao_titulo'],
        'mensagem': 'Comprovante oficial de votacao'
    }
    
    # Formatar para exibição amigável
    qr_string = f"""=== COMPROVANTE DE VOTAÇÃO ===

Token: {token}
Data/Hora: {qr_data['data_hora']}
Eleicao: {qr_data['eleicao']}
Candidato: {qr_data['candidato']}

Este comprovante é pessoal e intransferível.
O token não está armazenado em nosso sistema - guarde com segurança!
"""
    
    # Gerar QR Code
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_string)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Converter para base64 para retornar na API
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return img_base64