# Guia rápido de diagnóstico

## A TUI não abre ou fica apertada

Abra em um terminal interativo, sem redirecionar stdin/stdout. Aumente a janela
para pelo menos 44 × 18; a partir de 100 colunas, opções e detalhes ficam lado a
lado. Se aparecer erro de `curses` ou terminal incompatível, tente:

```bash
bash steam-fix-menu.sh --plain
```

Use `?` dentro da TUI para consultar as teclas. `Esc` volta uma etapa, sem
configurar nada. Para rolar detalhes longos, pressione Tab e depois ↑/↓.

O andamento das operações e seus resultados ficam também em
`~/.local/state/proton-online-fix-helper/logs/` (ou em `XDG_STATE_HOME`). O caminho
do log é exibido no resultado. Esses arquivos não devem ser publicados sem revisão.

## O jogo não aparece

Use **Informar caminho de outro jogo/executável**. Confira que o jogo está
instalado e existe uma versão Windows. A biblioteca pode não estar acessível
fora do sandbox no Steam Flatpak.

## Não aparece prefixo

Abra o jogo com Proton uma vez pelo Steam. A pasta costuma ser
`steamapps/compatdata/ID/pfx`, mas o ID de atalhos não-Steam não é o AppID do jogo.
Não crie nem apague prefixos aleatoriamente: eles podem conter seus saves.

## O jogo abre, mas não conecta

- Confiram versão do jogo e pacote em ambas as máquinas.
- Confirmem que não estão misturando uma sessão modificada com uma incompatível.
- Reiniciem o jogo depois de aplicar alterações.
- Coletem o erro real de conexão. Listar salas não prova que o P2P funciona.

Jogos Unity costumam registrar `Player.log` sob:

```text
PREFIXO/pfx/drive_c/users/steamuser/AppData/LocalLow/FABRICANTE/JOGO/
```

## `Application load error`

Pode ocorrer antes da inicialização do jogo. Confirme executável, diretório de
trabalho, prefixo e arquivos do pacote. O código sozinho não identifica a causa;
um override pode ajudar em alguns casos, mas não é garantia.

## `Cert is not authorized for appid X, only Y`

Indica uma incompatibilidade entre a autorização do certificado e o AppID usado
na conexão. **Não significa simplesmente que falta carregar uma DLL.**

Não troque IDs ao acaso. A correção depende da licença, do pacote e da sessão
dos dois jogadores. O override de DLLs não resolve necessariamente esse erro de
conexão; ele apenas permite que o pacote local seja carregado.

Se você já usa o patch `netsock.so` do SLSsteam, a ação avançada **Patch de rede
(SteamSockets)** pode configurar o `LD_AUDIT` nas opções de inicialização da
Steam. Feche a Steam antes de aplicar; um backup de `localconfig.vdf` é criado.
A opção não garante conexão: os dois jogadores precisam de versão, pacote e
AppID falso compatíveis. O projeto não baixa nem inclui o patch. Pela CLI:

```bash
bash steam-dll-fix.sh netsock --appid 4210580 --status
bash steam-dll-fix.sh netsock --appid 4210580 --apply
```

Para verificar o que está ativo:

```bash
bash steam-dll-fix.sh netsock --appid 4210580 --status
```

O diagnóstico lê `audit_patch.log`, o processo do jogo e o `Player.log` do
prefixo. Remova a opção com `--remove` se ela não ajudar.

## `Unsupported SteamUtils version`

Pode indicar interfaces incompatíveis ou loaders conflitantes. Não ative duas
pilhas de hooks sem saber se são compatíveis. Confira os arquivos do pacote e
as versões de Steam/Proton. A heurística do assistente não cobre todo conflito.

## Como reportar

Inclua distribuição, Steam nativo/Flatpak, Proton, jogo/versão, ação escolhida,
resultado esperado e o trecho relevante do erro. Remova SteamIDs, tokens,
chaves de API e informações pessoais. Não envie DLLs ou arquivos de jogos.
