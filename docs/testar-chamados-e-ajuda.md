# Testar chamados e central de ajuda

Se já tinha a versão anterior, atualize o código e execute, com sua virtualenv ativa:

```bash
python manage.py migrate
python manage.py bootstrap_desk
python manage.py runserver
```

No Windows, você também pode substituir `python` por `.\.venv\Scripts\python.exe`, sem ativar a virtualenv. Os comandos preservam usuários e chamados existentes. O bootstrap inclui os dez artigos iniciais sem sobrescrever orientações que a TI já alterou.

## Preparar as contas

Entre com o administrador criado por `python manage.py createsuperuser`. Em Administração → Usuários, crie uma conta de servidor sem grupos de TI e outra no grupo Técnicos. Use senhas próprias; não há credenciais padrão.

## Testar uma dúvida do início ao fim

1. Entre com a conta do servidor e abra Central de ajuda.
2. Pesquise por “impressora” ou escolha uma categoria.
3. Leia uma orientação e avalie se ela ajudou.
4. Use Enviar dúvida sobre este artigo. Confira se o assunto e a categoria foram preenchidos e selecione sua unidade.
5. Descreva sua pergunta e envie. Guarde o protocolo; o artigo consultado aparecerá nos detalhes.
6. Saia e entre como técnico. Abra Chamados e filtre pelo tipo Dúvida / orientação e por Sem responsável.
7. Abra a pergunta e selecione Assumir chamado. Ela passa para Em triagem, atribuída ao técnico conectado.
8. Na Área de atendimento, passe para Em atendimento e salve. Envie uma mensagem pública com a orientação.
9. Preencha Resposta / orientação e selecione Resolvido.
10. Volte à conta do servidor. Leia a resposta, confirme a solução ou reabra e explique o que ainda precisa de ajuda.

Confira que a conta do servidor vê somente seus chamados, enquanto a conta de técnico vê a fila completa.

## Testar os artigos

1. Como técnico, abra Central de ajuda → Gerenciar artigos → Novo artigo.
2. Preencha título, resumo e orientações, mantendo a publicação desmarcada.
3. Salve o rascunho. Abra seu endereço com a conta de servidor: o artigo não deve ser acessível.
4. Volte como técnico, edite e marque Publicar na central de ajuda.
5. Confira que o servidor agora consegue pesquisar e ler o artigo.
6. Avalie o artigo como servidor. Como técnico, veja o resultado no gerenciamento.
7. Retire a publicação para voltar ao estado de rascunho, preservando o conteúdo.

## Testes automáticos

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Os testes criam banco temporário e não usam nem apagam seus chamados. As capturas em `docs/screenshots/` usam dados fictícios; os exemplos não são adicionados ao banco principal pelo bootstrap.
