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

    # Abre arquivo para escrita
    with open(caminho_saida, "wb") as arquivo:
        while True:
            dados, _ = sock.recvfrom(BUFFER_SIZE)

            # Marca fim da transmissão
            if dados == b'FIM_ARQUIVO':
                break

            arquivo.write(dados)

    print(f"Arquivo devolvido salvo em: {caminho_saida}")
    return caminho_saida


def enviar_arquivo(sock, nome_arquivo):
    """
    Função criada pela Pessoa 1 para organizar o envio.
    Isso será essencial para implementar RDT 3.0 depois.
    """

    # Verifica se o arquivo existe no diretório atual
    if not os.path.exists(nome_arquivo):
        print('Arquivo não encontrado.')
        return

    # Envia inicialmente só o nome do arquivo para o servidor
    sock.sendto(os.path.basename(nome_arquivo).encode('utf-8'), (SERVER_HOST, SERVER_PORT))

    # Abre o arquivo em modo binário
    with open(nome_arquivo, 'rb') as arquivo:
        while True:
            # Lê um bloco de até 1024 bytes
            dados = arquivo.read(BUFFER_SIZE)

            # Se não tiver mais dados, encerra
            if not dados:
                break

            # Envia o bloco ao servidor
            sock.sendto(dados, (SERVER_HOST, SERVER_PORT))

    # Marca fim da transmissão
    sock.sendto(b'FIM_ARQUIVO', (SERVER_HOST, SERVER_PORT))

    print('Arquivo enviado com sucesso.')

def main():

    # Socket UDP do cliente
    cliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Solicita ao usuário o nome do arquivo que vai ser enviado
    nome_arquivo = input('Digite o nome do arquivo que deseja enviar: ')

    # Envio do arquivo (agora modularizado)
    enviar_arquivo(cliente, nome_arquivo)

    # Recebe o arquivo devolvido pelo servidor
    receber_arquivo_devolvido(cliente, ".")

    # Fecha o socket após terminar tudo
    cliente.close()


if __name__ == "__main__":
    main()