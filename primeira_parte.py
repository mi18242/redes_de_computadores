import socket
import os

# Tam max de cada pacote enviado via UDP
BUFFER_SIZE = 1024

# Endereço e porta
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000


def receber_arquivo_devolvido(sock, pasta_saida="."):
    """
    Recebe do servidor o arquivo devolvido.
    O servidor manda primeiro o nome do arquivo e depois os dados,
    finalizando com b'FIM_ARQUIVO'.
    """
    # Recebe o nome do arquivo devolvido
    nome_bytes, _ = sock.recvfrom(BUFFER_SIZE)
    nome_arquivo = nome_bytes.decode('utf-8', errors='ignore').strip()

    caminho_saida = os.path.join(pasta_saida, nome_arquivo)

    # Recebe os bytes do arquivo até o marcador de fim
    with open(caminho_saida, "wb") as arquivo:
        while True:
            dados, _ = sock.recvfrom(BUFFER_SIZE)

            if dados == b'FIM_ARQUIVO':
                break

            arquivo.write(dados)

    print(f"Arquivo devolvido salvo em: {caminho_saida}")
    return caminho_saida


# Socket UDP do cliente
cliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Solicita ao usuário o nome do arquivo que vai ser enviado
nome_arquivo = input('Digite o nome do arquivo que deseja enviar: ')

# Verifica se o arquivo existe no diretório atual
if not os.path.exists(nome_arquivo):
    print('Arquivo não encontrado.')
else:
    # Envia inicialmente só o nome do arquivo para o servidor
    cliente.sendto(os.path.basename(nome_arquivo).encode('utf-8'), (SERVER_HOST, SERVER_PORT))

    # Abre o arquivo em modo binário
    with open(nome_arquivo, 'rb') as arquivo:
        while True:
            # Lê um bloco de até 1024 bytes
            dados = arquivo.read(BUFFER_SIZE)

            # acaba, se não tiver mais dados
            if not dados:
                break

            # Envia o bloco lido ao servidor
            cliente.sendto(dados, (SERVER_HOST, SERVER_PORT))

    # Fim da transmissão
    cliente.sendto(b'FIM_ARQUIVO', (SERVER_HOST, SERVER_PORT))

    print('Arquivo enviado com sucesso.')

    # Recebe o arquivo devolvido pelo servidor
    receber_arquivo_devolvido(cliente, ".")

# Fecha o socket após terminar tudo
cliente.close()