# Integrantes
João Pedro Marinho de Souza  
Ismael Álvaro Lima da Silva  
Milla Rwana de Araújo Silva  
Rayssa Vitória Lima da Silva  

# Instruções de Execução
1. Inicie o servidor
> python servidor.py

2. Em outro terminal, execute o cliente
> python primeira_parte.py

3. Digite o nome do arquivo quando solicitado

# Funcionamento
O cliente envia o pacote em pacotes de até 1024 btyes via UDP  
O servidor recebe, salva, renomeia com o prefixo "leilao_" e devolve o arquivo ao cliente

# Testes realizados
Arquivo "teste.txt" (< 1024 bytes)  
Arquivo "imagem_pequena.png" (< 1024 bytes)  
Arquivo "imagem.png" (> 1024 bytes)  

No teste do arquivo "imagem.png", que é maior que 1024 bytes, foi observado a perda de dados, resultando em um arquivo incompleto. Isso ocorre devido às características do protocolo UDP, que não
garante entrega confiável.
