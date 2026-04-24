import socket
import os

# Tam max de cada pacote enviado via UDP
BUFFER_SIZE = 1024

# Endereço e porta
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000

# Socket UDP do cliente
cliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Solicita ao usuário o nome do arquivo que vai ser enviado
nome_arquivo = input('Digite o nome do arquivo que deseja enviar: ')

# Verifica se o arquivo exsite no diretório atual
if not os.path.exists(nome_arquivo):
    print('Arquivo não encontrado.')
else:
    # Envia inicialmente só o nome do arquivo pro servidor
    cliente.sendto(os.path.basename(nome_arquivo).encode(), (SERVER_HOST, SERVER_PORT))

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

# Fecha o socket após terminar tudo 
cliente.close()
