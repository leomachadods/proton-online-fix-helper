# LuaTools, OnlineFix e Proton: o que este projeto faz

## São três partes diferentes

1. **Steam/LuaTools**: contexto em que o jogo e o pacote podem ter sido instalados.
2. **Pacote do jogo**: DLLs, configurações e outros arquivos específicos daquela versão.
3. **Proton**: ambiente usado para executar o programa Windows no Linux.

Este projeto atua principalmente na terceira parte: selecionar o prefixo correto
e configurar o carregamento das DLLs locais. Também importa um pacote local
quando solicitado. Não é um plugin do LuaTools, não lê ou instala scripts Lua e
não altera seus mecanismos de instalação ou autorização.

## Por que copiar o pacote pode não bastar?

O Wine decide entre implementações internas e DLLs nativas conforme suas regras
e os overrides configurados. Uma DLL presente no diretório não prova que foi
carregada. Tampouco uma entrada de jogo na biblioteca prova licença ou uma sessão
de rede válida.

Por isso o fluxo recomendado é:

1. Confirmar versão do jogo e pacote com o outro jogador.
2. Abrir uma vez pelo Proton para criar o prefixo.
3. Selecionar esse prefixo no assistente, não um ID parecido de outra instalação.
4. Configurar os overrides e reiniciar o jogo.
5. Testar conexão e ler o log caso falhe.

## O que não é inferido

O assistente não assume que LuaTools está instalado, não tenta descobrir posse
de licença a partir de `appmanifest` e não presume que `FakeAppId=RealAppId`
seja uma solução válida para todo jogo. Não corrige incompatibilidades entre
versões de pacotes ou autenticação de serviços externos.

O comportamento das diferentes versões do LuaTools não foi validado por uma suíte
de integração neste projeto. Reporte problemas com versão, passos e logs
sanitizados, sem distribuir arquivos proprietários.
