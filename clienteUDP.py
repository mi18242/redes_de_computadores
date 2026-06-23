import socket
import os

BUFFER_SIZE = 1024
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000
TIMEOUT_VAL = 1.0

def enviar_arquivo_rdt(sock, caminho_arquivo):
    """Envia o arquivo fragmentado para o servidor usando RDT 3.0."""
    seq_atual = 0
    
    # Prepara os blocos (Nome, Conteúdo fragmentado, Fim)
    blocos = [os.path.basename(caminho_arquivo).encode('utf-8')]
    
    with open(caminho_arquivo, 'rb') as f:
        while True:
            # Lê 1021 bytes para que com 'X|' não ultrapasse 1024 bytes
            dados = f.read(BUFFER_SIZE - 3)
            if not dados:
                break
            blocos.append(dados)
    blocos.append(b'FIM_ARQUIVO')

    print("Iniciando envio via RDT 3.0...")
    for bloco in blocos:
        pacote = f"{seq_atual}|".encode() + bloco
        
        while True:
            try:
                sock.sendto(pacote, (SERVER_HOST, SERVER_PORT))
                print(f"[RDT 3.0] Pacote enviado -> SEQ {seq_atual}")

                # Aguarda o ACK do servidor dentro do limite de tempo
                ack_dados, _ = sock.recvfrom(BUFFER_SIZE)
                ack_msg = ack_dados.decode().strip()

                if ack_msg == f"ACK:{seq_atual}":
                    print(f"[RDT 3.0] ACK confirmado -> {ack_msg}")
                    break
                else:
                    print(f"[RDT 3.0] ACK duplicado/inválido ({ack_msg}). Tratando retransmissão...")
            except socket.timeout:
                print(f"[TIMEOUT] Sem resposta para o pacote SEQ {seq_atual}. Retransmitindo...")
        
        seq_atual = 1 - seq_atual

def receber_devolucao_rdt(sock, pasta_saida="."):
    """Recebe o arquivo devolvido pelo servidor usando RDT 3.0.
    Adicionado filtro para descartar ACKs redundantes residuais do servidor."""
    sock.settimeout(None) # Desativa temporariamente o timeout para aguardar o processamento do servidor
    
    esperado = 0
    arquivo = None
    caminho_final = ""

    print("Aguardando devolução do arquivo pelo servidor...")
    while True:
        pacote, server_addr = sock.recvfrom(BUFFER_SIZE)
        
        try:
            # Filtro de pacotes inválidos.
            # Se o pacote não contiver o caractere separador '|', significa que é um ACK residual
            # (enviado de forma redundante pelo servidor no fim da etapa anterior) flutuando na rede.
            # Ignoramos ele para evitar o erro 'not enough values to unpack' no .split().
            if b'|' not in pacote:
                # Se for um ACK perdido/antigo flutuando na rede, ignora e continua esperando
                continue

            cabecalho, dados = pacote.split(b'|', 1)
            seq = int(cabecalho.decode())
            print(f"[RDT 3.0] Pacote da devolução recebido -> SEQ {seq}")

            if seq == esperado:
                if arquivo is None:
                    # Reconstroi o nome do arquivo devolvido
                    nome_arquivo = dados.decode('utf-8', errors='ignore').strip()
                    caminho_final = os.path.join(pasta_saida, nome_arquivo)
                    arquivo = open(caminho_final, "wb")
                    print(f"Baixando arquivo devolvido: {nome_arquivo}")
                elif dados == b'FIM_ARQUIVO':
                    print("[RDT 3.0] Fim do arquivo recebido com sucesso.")
                    # Envia a confirmação final para  servidor fechar a concexão
                    ack = f"ACK:{seq}"
                    sock.sendto(ack.encode(), server_addr)
                    arquivo.close()
                    break
                else:
                    arquivo.write(dados)

                ack = f"ACK:{seq}" # envia o ACK de confirm do pacote atual
                sock.sendto(ack.encode(), server_addr)
                esperado = 1 - esperado
            else:
                print(f"[RDT 3.0] Pacote duplicado da devolução ({seq}). Reenviando ACK correspondente.")
                ack = f"ACK:{1 - esperado}"
                sock.sendto(ack.encode(), server_addr)
        except Exception as e:
            print(f"[ERRO RECEBIMENTO CLIENTE] {e}")

    print(f"Arquivo salvo com sucesso em: {caminho_final}")

def main():
    cliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cliente.settimeout(TIMEOUT_VAL)

    nome_arquivo = input('Digite o nome do arquivo que deseja enviar: ').strip()

    if not os.path.exists(nome_arquivo):
        print('Arquivo não encontrado no diretório atual.')
        cliente.close()
        return

    try:
        # Envia o arquivo usando o protocolo confiável
        enviar_arquivo_rdt(cliente, nome_arquivo)
        print("Envio concluído. Modificando canal para recepção...")
        
        # Recebe de volta o arquivo renomeado pelo servidor
        receber_devolucao_rdt(cliente, ".")
    except Exception as e:
        print(f"[ERRO EXECUÇÃO] {e}")
    finally:
        cliente.close()

if __name__ == "__main__":
    main()