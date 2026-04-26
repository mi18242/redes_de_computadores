import socket
import os

HOST = '0.0.0.0'     # Faz o servidor escutar em todas as interfaces de rede
PORT = 5000          # Porta onde o servidor ficará disponível
BUFFER_SIZE = 1024   # Tamanho máximo de cada pacote 
PREFIXO = "leilao_"  # Prefixo que será adicionado ao nome do arquivo recebido


def receber_arquivo(sock, nome_arquivo):
    """
    Recebe os fragmentos do cliente e salva o arquivo já com o prefixo leilao_.
    """
    nome_arquivo = os.path.basename(nome_arquivo)
    novo_nome = PREFIXO + nome_arquivo

    # Abre o arquivo em modo escrita binária
    with open(novo_nome, "wb") as f:
        while True:
            # Recebe um pacote de dados do cliente
            dados, _ = sock.recvfrom(BUFFER_SIZE)

            # Se receber o marcador de fim, encerra o loop
            if dados == b'FIM_ARQUIVO':
                break

            # Escreve os dados recebidos no arquivo
            f.write(dados)

    # Retorna o nome do arquivo salvo
    return novo_nome


def enviar_arquivo(sock, client_addr, caminho_arquivo):
    """
    Reenvia ao cliente o arquivo já salvo no servidor.
    Primeiro envia o nome do arquivo e depois os bytes em blocos de até 1024.
    """
    sock.sendto(os.path.basename(caminho_arquivo).encode('utf-8'), client_addr)

    with open(caminho_arquivo, "rb") as f:
        while True:
            bloco = f.read(BUFFER_SIZE)
            if not bloco:
                break
            sock.sendto(bloco, client_addr)

    sock.sendto(b'FIM_ARQUIVO', client_addr)


def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    servidor.bind((HOST, PORT))

    print(f"Servidor UDP escutando em {HOST}:{PORT}")

    while True:
        # Recebe o nome do arquivo enviado pelo cliente
        nome_bytes, client_addr = servidor.recvfrom(BUFFER_SIZE)
        nome_arquivo = nome_bytes.decode('utf-8', errors='ignore').strip()

        print(f"Recebendo arquivo: {nome_arquivo} de {client_addr}")

        # Recebe e salva o arquivo com prefixo
        caminho_arquivo = receber_arquivo(servidor, nome_arquivo)

        print(f"Arquivo salvo como: {caminho_arquivo}")

        # Devolve o arquivo renomeado ao cliente
        enviar_arquivo(servidor, client_addr, caminho_arquivo)

        print(f"Arquivo devolvido ao cliente: {client_addr}")


if __name__ == "__main__":
    main()