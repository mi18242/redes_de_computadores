import socket
import sys

BUFFER_SIZE = 1024
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000
TIMEOUT_VAL = 1.5  # Tempo pra esperar o ACK antes de transmitir de novo

def enviar_mensagem_rdt(sock, mensagem, seq_atual):
    """
    Envia uma string de texto usando o protocolo RDT 3.0 
    Garante que o comando chegue ao despachante do servidor mesmo com 30% de perda.
    """
    # seq|dados
    pacote = f"{seq_atual}|{mensagem}".encode('utf-8')
    
    while True:
        try:
            # Envia o pacote pro servidor
            sock.sendto(pacote, (SERVER_HOST, SERVER_PORT))
            print(f"[RDT 3.0] Enviando: '{mensagem}' com SEQ {seq_atual}...")

            # timeout para aguardar a resposta 
            sock.settimeout(TIMEOUT_VAL)
            
            # Espera resposta do servidor
            resposta, _ = sock.recvfrom(BUFFER_SIZE)
            msg_recebida = resposta.decode('utf-8').strip()

            # Servidor responde ACK:<seq>
            if msg_recebida == f"ACK:{seq_atual}":
                print(f"[RDT 3.0] ACK {seq_atual} confirmado pelo servidor!")
                break  # Pacote foi entregue com sucesso
            else:
                print(f"[RDT 3.0] ACK incorreto ou duplicado ({msg_recebida}). Tentando novamente...")

        except socket.timeout:
            # Se estourar o tempo e o ACK não vier, o RDT 3.0 retransmite o pacote
            print(f"[TIMEOUT] Sem resposta para o pacote SEQ {seq_atual}. Retransmitindo comando...")
            
    # Seq alternada 
    return 1 - seq_atual

def receber_resposta_servidor(sock):
    """
    Após o envio do comando e confirmação do ACK, o cliente fica 
    esperando o resultado textual do comando processado pela Thread
    """
    # Remove o timeout 
    sock.settimeout(None)
    
    try:
        # Recebe o resultado do comando (ex: "Você está online", "Lista de leilões...", etc.)
        dados, _ = sock.recvfrom(BUFFER_SIZE)
        return dados.decode('utf-8')
    except Exception as e:
        return f"[ERRO AO RECEBER RESPOSTA] {e}"

def main():
    cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # O cliente RDT 3.0 começa controlando o bit de sequência em 0
    seq_atual = 0
    
    print("=" * 60)
    print("          BEM-VINDO AO AUCTIONCIN          ")
    print("=" * 60)
    print("Comandos disponíveis:")
    print("  -> login <seu_nome>")
    print("  -> logout")
    print("  -> create <produto> <preço_inicial> <tempo_segundos>")
    print("  -> list")
    print("  -> bid <id_leilao> <seu_lance>")
    print("  -> sair (encerra o programa cliente)")
    print("-" * 60)

    try:
        while True:
            comando = input("\nDigite o comando: ").strip()
            
            if not comando:
                continue
                
            if comando.lower() == 'sair':
                print("Encerrando aplicação cliente. Até logo!")
                break

            seq_atual = enviar_mensagem_rdt(cliente_socket, comando, seq_atual)
            
            print("Processando comando no servidor...")
            resposta_leilao = receber_resposta_servidor(cliente_socket)
            
            print("\n[RESPOSTA DO SERVIDOR]:")
            print(resposta_leilao)
            print("-" * 50)

    except KeyboardInterrupt:
        print("\nCliente finalizado via teclado.")
    finally:
        cliente_socket.close()

if __name__ == "__main__":
    main()