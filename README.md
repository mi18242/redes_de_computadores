# Projeto de Fundamento de Redes de Computadores
## Integrantes
João Pedro Marinho de Souza - jpms3  
Ismael Álvaro Lima da Silva - ials  
Milla Rwana de Araújo Silva - mras3  
Rayssa Vitória Lima da Silva - rvls2  

## Instruções de Execução
1. Iniciar o Servidor
Abra um terminal e execute:
> python3 servidor_integrado.py

2. Iniciar os clientes
Para cada cliente, abra um novo terminal e execute:
> python3 cliente_leilao.py

## Comandos
### login <nome_do_usuario>
Conecta o cliente ao sistema com um nome único.
>Não será possível realizar qualquer outro comando sem login

### create <produto> <preço> <tempo_segundos>
Cria um novo leilão.  
produto: nome do item  
preço: preço inicial do item  
tempo_segundos: por quantos segundos esse item será leiloado

### list
Lista todos os leilões ativos.

### bid <id_leilao> <valor>
Dá um lance em um leilão existente, até 5 lances podem ser feitos para um leilão.
id_leilao: número identificador do leilão  
valor: valor do lance (deve ser maior que o lance atual)
>📢 Todos os usuários conectados recebem notificação do lance via broadcast assim que seu próximo comando for executado, se seu objetivo é só ver a notificação pressione enter

### status
Mostra o status de todos os leilões (ativos e encerrados), incluindo o maior lance e vencedor.

### logout
Desconecta o usuário do sistema.

## Testes realizados
### Teste 1
O leilão se encerra pois 5 lances foram realizados.
| Passo | Terminal 1                    | Terminal 2                | Terminal 3                |
|-------|-------------------------------|---------------------------|---------------------------|
| 1     | python3 servidor_integrado.py | python3 cliente_leilao.py | python3 cliente_leilao.py |
| 2     |                               | login joao                | login maria               |
| 3     |                               | create Carro 1000 60      |                           |
| 4     |                               |                           | bid 1 1001                |
| 5     |                               | bid 1 1100                |                           |
| 6     |                               |                           | bid 1 1101                |
| 7     |                               | bid 1 2000                |                           |
| 8     |                               |                           | bid 1 2001                |

### Teste 2
O leilao se encerra por tempo
| Passo | Terminal 1                    | Terminal 2                |
|-------|-------------------------------|---------------------------|
| 1     | python3 servidor_integrado.py | python3 cliente_leilao.py |
| 2     |                               | login joao                |
| 3     |                               | create Carro 1000 1       |
