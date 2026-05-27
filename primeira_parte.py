import socket
import os

# Tam max de cada pacote enviado via UDP
BUFFER_SIZE = 1024

# Endereço e porta
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000

# Timeout do RDT 3.0
TIMEOUT = 2


def esperar_ack(sock, seq):
    """
    Espera ACK do pacote enviado.
    Retorna True se receber ACK correto.
    """

    try:
        ack, _ = sock.recvfrom(BUFFER_SIZE)
        ack = ack.decode('utf-8')

        if ack == f"ACK:{seq}":
            print(f"[CLIENTE] ACK {seq} recebido")
            return True

        print("[CLIENTE] ACK incorreto recebido")
        return False

    except socket.timeout:
        print(f"[CLIENTE] Timeout do pacote {seq}")
        return False


def enviar_pacote_rdt(sock, dados, seq):
    """
    Envia pacote usando lógica do RDT 3.0.
    """

    cabecalho = f"{seq}|".encode('utf-8')
    pacote = cabecalho + dados

    while True:
        print(f"[CLIENTE] Enviando pacote {seq}")

        sock.sendto(pacote, (SERVER_HOST, SERVER_PORT))

        if esperar_ack(sock, seq):
            break

        print(f"[CLIENTE] Reenviando pacote {seq}")


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

    print(f"[CLIENTE] Arquivo devolvido salvo em: {caminho_saida}")
    return caminho_saida


def enviar_arquivo(sock, nome_arquivo):
    """
    Função criada pela Pessoa 1 para organizar o envio.
    Isso será essencial para implementar RDT 3.0 depois.
    Também retorna se enviou ou não
    """

    # Verifica se o arquivo existe no diretório atual
    if not os.path.exists(nome_arquivo):
        print('Arquivo não encontrado.')
        return False

    # Número de sequência inicial
    seq = 0

    # Envia inicialmente só o nome do arquivo para o servidor
    enviar_pacote_rdt(
        sock,
        os.path.basename(nome_arquivo).encode('utf-8'),
        seq
    )

    seq = 1 - seq

    # Abre o arquivo em modo binário
    with open(nome_arquivo, 'rb') as arquivo:
        while True:
            # Lê um bloco de até 1024 bytes
            dados = arquivo.read(BUFFER_SIZE - 2)

            # Se não tiver mais dados, encerra
            if not dados:
                break

            # Envia o bloco ao servidor
            enviar_pacote_rdt(sock, dados, seq)

            # Alterna número de sequência (0 e 1)
            seq = 1 - seq

    # Marca fim da transmissão
    enviar_pacote_rdt(sock, b'FIM_ARQUIVO', seq)

    print('[CLIENTE] Arquivo enviado com sucesso.')

    # Diz para o servidor que esta pronto para receber
    sock.sendto(b'PRONTO_RECEBER', (SERVER_HOST, SERVER_PORT))

    return True


def main():
    # Socket UDP do cliente
    cliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Configura timeout do RDT
    cliente.settimeout(TIMEOUT)

    # Solicita ao usuário o nome do arquivo que vai ser enviado
    nome_arquivo = input('Digite o nome do arquivo que deseja enviar: ')

    # Envio do arquivo (agora modularizado)
    sucesso = enviar_arquivo(cliente, nome_arquivo)

    # Se o arquivo foi enviado, recebe o arquivo devolvido pelo servidor
    if sucesso:
        cliente.settimeout(None) # Garante que recebe o arquivo de volta, sem tempo limite
        receber_arquivo_devolvido(cliente, ".")

    # Fecha o socket após terminar tudo
    cliente.close()


if __name__ == "__main__":
    main()
