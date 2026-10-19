# Ativar a demonstração do Service Desk no GitHub Pages

Os arquivos do site estão na pasta `docs`. A publicação usa a branch `main` e não exige configurar Python, banco de dados, senhas ou comandos no computador do visitante.

## Ativação no GitHub

1. Entre na conta que administra o repositório e abra: https://github.com/Th3Destroyer/TCC/settings/pages
2. Em **Build and deployment**, na opção **Source**, escolha **Deploy from a branch**.
3. Em **Branch**, selecione **main**. Na pasta, selecione **/docs**.
4. Clique em **Save**.
5. Aguarde o build. O endereço do site e o estado da publicação aparecem nessa mesma tela. O processo também pode ser acompanhado na aba **Actions** do repositório.

Endereço esperado após a publicação: https://th3destroyer.github.io/TCC/

O arquivo `docs/.nojekyll` permite servir o site diretamente como HTML, CSS e JavaScript. As rotas usam fragmentos, como `#/chamados` e `#/ajuda`, para que os links funcionem dentro de `/TCC/` e possam ser recarregados.

Se a opção de Pages estiver indisponível por causa do plano ou da visibilidade do repositório, verifique os requisitos informados pelo GitHub. Não é necessário tornar o código público para preparar os arquivos; a disponibilidade de publicação de um repositório privado depende do plano. Não altere a visibilidade sem autorização do proprietário.

## O que o visitante consegue experimentar

- Entrar como solicitante ou técnico, sem credenciais reais.
- Acompanhar o painel, pesquisar e filtrar chamados.
- Abrir um chamado ou enviar uma dúvida sobre um artigo.
- Trocar para técnico, assumir, responder e resolver o chamado de exemplo.
- Voltar a solicitante, confirmar a solução ou reabrir.
- Consultar orientações, avaliar artigos, criar rascunhos e simular publicações no perfil de técnico.
- Consultar indicadores e exportar os chamados de exemplo em CSV.

O site não atende chamados reais e não executa Django. As alterações ficam somente no navegador e podem ser apagadas com **Restaurar dados de exemplo**. Trocar de computador ou navegador não transfere os exemplos criados. Não informe dados pessoais ou senhas nos formulários de demonstração.

## Manutenção

Execute `python scripts/build_pages.py` após alterar os estilos ou os artigos iniciais. Publique os arquivos de `docs/` junto com o código. As alterações na branch configurada acionam a publicação do Pages.

O teste de navegação está em `scripts/test_pages.py`. Para desenvolvimento, com Playwright/Chromium instalado, inicie um servidor HTTP na raiz do repositório (`python -m http.server 8010`) e execute o teste em outro terminal (`python scripts/test_pages.py`). O endereço pode ser alterado pela variável `PAGES_TEST_URL`. O teste usa um contexto novo de navegador e dados fictícios, sem alterar o banco do Django.

Para instalar a aplicação real, siga o README do repositório. Hospedar Django exige um servidor capaz de executar Python e manter o banco; o GitHub Pages serve somente os arquivos estáticos da demonstração.
