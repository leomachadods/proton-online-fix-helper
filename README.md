# Proton Online Fix Helper

**Um assistente TUI para configurar jogos Windows com pacotes OnlineFix no Linux/Proton.**

Escolha o jogo instalado na Steam, confirme o prefixo e o Proton, e configure o
carregamento das DLLs. Também permite importar um pacote local com backup.

> Projeto comunitário e independente. Não é afiliado à Valve, Steam, LuaTools ou
> OnlineFix. Não inclui jogos, DLLs, licenças, arquivos Lua ou downloads de fixes.

## Qual problema ele tenta resolver?

Um pacote pode estar na pasta correta e ainda assim não ser carregado pelo Wine.
Por exemplo, dependendo da configuração, o Proton pode escolher sua implementação
interna de `winmm.dll` em vez da DLL local do pacote.

O assistente configura um **DLL override** no prefixo selecionado, como
`winmm=n,b`: tenta a DLL nativa primeiro e permite fallback para a interna.

Isso **não é uma correção universal para multiplayer**. Entrar na lista de salas
não garante conexão P2P, autenticação, versão compatível ou acesso ao backend do jogo.

## E quando eu uso LuaTools?

O foco inclui instalações em que o pacote foi colocado pela integração do
**LuaTools com OnlineFix na Steam**. O assistente verifica a instalação local e
configura o Proton; ele **não modifica o LuaTools nem presume como cada versão
instala os arquivos**.

Mesmo que o LuaTools tenha colocado os arquivos, ainda pode faltar o override no
prefixo usado para executar o jogo. A importação de arquivos e a configuração do
Proton são etapas distintas. Veja [LuaTools e diagnóstico](docs/LUATOOLS.md).

## Requisitos

- Linux com Steam e Proton instalados.
- Python **3.9+** e Bash **4+** para o menu.
- Ferramentas usuais do Linux: `awk`, `sed`, `grep`, `find`, `stat` e `mktemp`.
- O jogo deve ter sido aberto ao menos uma vez com Proton para criar o prefixo.
- Um pacote específico para a versão do jogo, obtido de uma origem confiável,
  caso seja necessária a importação.

Não execute como root ou com `sudo`. Windows e macOS não são suportados.
O Steam Flatpak é detectado pelo menu, mas permissões do sandbox podem exigir
ajustes manuais; não há garantia de compatibilidade.

## Começar em 3 passos

1. Baixe e extraia o ZIP deste repositório, ou clone-o:

   ```bash
   git clone https://github.com/leomachadods/proton-online-fix-helper.git
   cd proton-online-fix-helper
   ```

2. Abra o menu:

   ```bash
   bash steam-fix-menu.sh
   ```

3. Escolha **jogo → prefixo → Proton** e selecione **Preparar e jogar**.
   O assistente configura o que faltar e abre o jogo; você não precisa escolher
   entre aplicar overrides e executar.

   Se um carregador comum não for encontrado, o assistente oferece escolher uma
   **pasta local com o pacote já extraído**, abrir com os arquivos atuais ou voltar.
   Essa detecção é uma heurística, não uma verificação completa do pacote.

Na tela de prefixos, a correspondência de **AppID + biblioteca** aparece primeiro
como **RECOMENDADO**. Cada opção mostra jogo, ID, caminho e Proton registrado.
Na terceira tela, o Proton registrado também aparece primeiro, quando instalado.
O programa não escolhe por você: confirme o número para continuar.

**Feche o jogo antes de importar arquivos ou alterar configurações.**
Mantenha toda a pasta do projeto junta: os `.sh` dependem de `lib/` e `steamfix/`.

## Menu simples

```text
[1] Preparar e jogar
[2] Aplicar correção sem abrir o jogo
[3] Opções avançadas
[4] Sair
```

Para uso normal, escolha **Preparar e jogar**. As opções técnicas ficam em
**Opções avançadas**, que tem um botão **Voltar** para retornar ao menu principal.

Se quiser jogar depois pela Steam, escolha **Aplicar correção sem abrir o jogo**.
Essa opção configura os overrides usando Proton, mas não executa o jogo.

**Não há redirecionamento automático para “servidores do OnlineFix”.** O assistente
configura o carregamento das DLLs locais; as DLLs e o jogo determinam os serviços
usados, que podem continuar sendo da Steam. Aplicar overrides não muda por si só
servidores, certificados, AppIDs ou compatibilidade entre salas. Não é possível
garantir a conexão multiplayer apenas pela conclusão da configuração.

## Navegação na TUI

A interface abre em tela cheia. A opção selecionada fica destacada; os detalhes
aparecem à direita. Em terminais mais estreitos, os detalhes ficam abaixo da
lista. A primeira opção de prefixo continua sendo a recomendada para o jogo,
quando houver uma correspondência de AppID e biblioteca.

| Tecla | Ação |
|---|---|
| **↑ / ↓** | Selecionar uma opção. Também aceita `j` / `k`. |
| **Enter** | Confirmar a opção destacada. |
| **Esc** | Voltar uma etapa; no menu principal, sair. |
| **/** | Buscar por nome, AppID ou caminho. Esc limpa a busca. |
| **Tab** | Alternar entre seleção e rolagem dos detalhes. |
| **PgUp / PgDn** | Rolar uma página na lista ou nos detalhes. |
| **Home / End** | Primeira ou última opção. |
| **?** | Abrir a ajuda de teclado. |

Nos campos de texto, use ←/→ para mover o cursor e Ctrl+U para limpar. Caminhos
com espaços são aceitos sem aspas. Nenhuma opção é executada apenas por movê-la:
é necessário confirmar com Enter.

A TUI usa `curses`, que acompanha o Python na maioria das distribuições Linux.
Requer um terminal de pelo menos **44 colunas × 18 linhas**; para duas colunas,
prefira **100 colunas ou mais**. Se curses não estiver disponível ou seu terminal
não for compatível, o menu numerado continua acessível:

```bash
bash steam-fix-menu.sh --plain
```

Durante operações, a TUI mostra o andamento e salva a saída em:

```text
~/.local/state/proton-online-fix-helper/logs/
```

Se `XDG_STATE_HOME` estiver definido, ele substitui `~/.local/state`. Logs podem
conter informações pessoais: revise-os antes de compartilhar. O painel de
resultado permite rolagem. Ao abrir um jogo, aguarde fechá-lo para retornar.
Ctrl+C sai da interface, mas **não encerra processos Proton já iniciados**.

## O que há nas opções avançadas

| Opção | Comportamento |
|---|---|
| Ver detalhes da configuração | Consulta o registro usando Proton; pode inicializar serviços do Wine. |
| Instalar arquivos de um pacote local | Copia arquivos locais, com confirmação, backup e tentativa de rollback. |
| Ver alterações propostas | Mostra overrides propostos, sem executar Proton nem abrir jogos. |
| Configurar sem abrir o jogo | Configura os overrides para as DLLs detectadas. |
| Desfazer configuração de DLLs | Remove os overrides das DLLs selecionadas; não desfaz importações. |

## Segurança e backup

DLLs são programas e executam com suas permissões. O projeto não verifica sua
autenticidade e não baixa nem executa pacotes automaticamente durante a importação.
Pacotes com links simbólicos ou arquivos especiais são recusados.

Arquivos substituídos ficam em `.steam-fix-backup-DATA/` dentro do jogo. Para
restaurar, feche o jogo e copie os originais de volta. Os arquivos novos listados
em `arquivos-copiados.txt` precisam ser avaliados separadamente: **remover overrides
não remove os arquivos importados**. Guarde o backup até confirmar o resultado.

Não use patches de memória em jogos com anti-cheat. O menu desativa a integração
legada de patch de certificados. A CLI também a deixa desligada por padrão.

## CLI (opcional)

```bash
# Ajuda
bash steam-dll-fix.sh --help

# Pré-visualizar sem executar Proton
bash steam-dll-fix.sh apply --path "/pasta/do/jogo" --compatdata 123 --dry-run

# Aplicar e abrir um jogo da biblioteca principal
bash steam-dll-fix.sh apply --appid 123
bash steam-dll-fix.sh launch --appid 123
```

Os números são exemplos. Não copie o ID do prefixo de outra pessoa.
Consulte [o guia de diagnóstico](docs/TROUBLESHOOTING.md) antes de alterar AppIDs.

## Limitações conhecidas

- O menu descobre jogos em várias bibliotecas, mas ainda **recusa prefixos em
  bibliotecas externas**: o backend pressupõe `compatdata` na raiz principal.
- A CLI tem descoberta mais limitada que o menu, especialmente no Steam Flatpak.
- Atalhos não-Steam podem ser usados no menu informando o caminho manualmente.
- Seleção automática de DLLs e executável é uma heurística; jogos com vários
  executáveis ou loaders não convencionais podem precisar de configuração manual.
- A verificação legada por timeout não é oferecida no menu; seu código ainda usa
  encerramento por nome e não deve ser usado com outra instância do jogo aberta.
- Não há garantia de funcionamento com toda versão de Steam, Proton ou pacote.
- Não é feita validação de licença, desativação de anti-cheat nem correção do
  servidor do jogo. Use apenas jogos e arquivos que você tem direito de utilizar.

## Organização e testes

```text
steam-fix-menu.sh       entrada do menu
menu.py                entrada Python
steamfix/              TUI curses, modo texto, descoberta e importação local
steam-dll-fix.sh        entrada da CLI
lib/                   módulos Bash do backend
tests/                 testes isolados
docs/                  diagnóstico e contexto do LuaTools
```

```bash
python3 -m unittest discover -s tests -v
```

Os testes usam arquivos temporários e Proton simulado; não alteram seus jogos.
Veja [CONTRIBUTING.md](CONTRIBUTING.md) para contribuir e
[PUBLISHING.md](docs/PUBLISHING.md) para publicar sua cópia no GitHub.

## Licença

[MIT](LICENSE). Pacotes de terceiros têm suas próprias licenças e não são incluídos.
