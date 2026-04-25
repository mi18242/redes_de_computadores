import socket  
import os     

HOST = '0.0.0.0'     # Faz o servidor escutar em todas as interfaces de rede
PORT = 5000          # Porta onde o servidor ficará disponível
BUFFER_SIZE = 1024   # Tamanho máximo de cada pacote 
PREFIXO = "leilao_"  # Prefixo que será adicionado ao nome do arquivo recebido


def receber_arquivo(sock, nome_arquivo):
  
    
    # Adiciona prefixo ao nome do arquivo
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
 
    
    # Envia primeiro o nome do arquivo 
    sock.sendto(os.path.basename(caminho_arquivo).encode(), client_addr)

    # Abre o arquivo em modo leitura binária 
    with open(caminho_arquivo, "rb") as f:
        while True:
         
            bloco = f.read(BUFFER_SIZE)

       
            if not bloco:
                break

            # Envia o bloco para o cliente
            sock.sendto(bloco, client_addr)

    # Envia marcador indicando fim do arquivo
    sock.sendto(b'FIM_ARQUIVO', client_addr)