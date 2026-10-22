# Como contribuir

1. Reproduza o problema em uma pasta temporária e adicione um teste.
2. Não teste alterações de prefixos em bibliotecas reais automaticamente.
3. Preserve códigos de saída: falhas de configuração não devem abrir o jogo.
4. Não use `eval`, `shell=True` ou `source` para ler dados de configuração.
5. Não baixe DLLs nem desative validações de segurança silenciosamente.
6. Documente alterações de comportamento e limitações no README.

```bash
python3 -m unittest discover -s tests -v
for file in *.sh lib/*.sh; do bash -n "$file" || exit 1; done
```

Mantenha os módulos pequenos: menu e importação em `steamfix/`; registro,
configuração e comandos Proton em `lib/`. Os testes não exigem Steam instalado.
