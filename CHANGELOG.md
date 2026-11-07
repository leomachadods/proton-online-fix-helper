# Changelog

## 1.2.0

- Ação avançada opt-in **Patch de rede (SteamSockets)**: verifica e configura o
  `LD_AUDIT` do patch SLSsteam nas opções de inicialização da Steam.
- Diagnóstico mostra patch, opções atuais, processo do jogo, `audit_patch.log`
  e erros recentes de conexão no `Player.log`.
- Gravação com backup automático de `localconfig.vdf`, verificação do resultado
  e exigência de Steam fechada; a opção pode ser removida.
- O projeto continua sem baixar, incluir ou validar patches; a ação não garante
  conexão online e não altera o fluxo principal de overrides de DLL.
- Ação principal para aplicar a configuração sem iniciar o jogo.
- Documentação esclarece que overrides não redirecionam servidores automaticamente.

## 1.1.0

- TUI em tela cheia, com setas, painel de detalhes, busca e ajuda de teclado.
- Layout responsivo e retorno entre etapas com Esc.
- Acompanhamento de operações sem misturar saída do Proton à interface.
- Logs locais com permissões restritas e painel de resultado com rolagem.
- Menu numerado anterior disponível com `--plain`.
- Testes de renderização, teclado, Unicode e fluxo real em pseudoterminal.

## 1.0.0

- Seleção de jogo, prefixo e Proton; correspondências recomendadas primeiro.
- Fluxo Preparar e jogar e submenu avançado.
- Importação local com backup, testes isolados e documentação.
