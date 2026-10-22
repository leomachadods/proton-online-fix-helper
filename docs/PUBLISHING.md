# Publicar no GitHub

Nome sugerido: **Proton Online Fix Helper**

Nome do repositório: **`proton-online-fix-helper`**

1. Crie um repositório vazio com esse nome no GitHub. Não gere README/licença
   pelo site: estes arquivos já estão aqui.
2. Na pasta do projeto, execute os testes e revise o que será enviado:

   ```bash
   python3 -m unittest discover -s tests -v
   git status --short
   ```

3. Faça o primeiro commit e envie, substituindo `SEU-USUARIO`:

   ```bash
   git add .
   git diff --cached --stat
   git commit -m "Initial release: Proton Online Fix Helper"
   git remote add origin git@github.com:leomachadods/proton-online-fix-helper.git
   git push -u origin main
   ```

4. Repositório deste projeto: https://github.com/leomachadods/proton-online-fix-helper

Nunca publique DLLs, jogos, scripts Lua de terceiros, saves, logs pessoais,
tokens ou configurações da sua instalação Steam. O `.gitignore` ajuda, mas
revise sempre os arquivos antes de enviar.

O projeto já tem workflow de testes do GitHub Actions. Nenhum repositório remoto
é criado por estes comandos locais até você configurar e executar o envio.
