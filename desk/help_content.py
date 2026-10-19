"""Orientações iniciais de suporte. O bootstrap não sobrescreve artigos editados."""

INITIAL_ARTICLES = [
    {
        "key": "abrir-acompanhar-chamado", "category": None, "featured": True,
        "title": "Como abrir e acompanhar um chamado?",
        "summary": "Veja como pedir suporte à TI e acompanhar cada etapa do atendimento.",
        "body": "1. Acesse Chamados no menu e selecione Novo chamado.\n2. Informe um assunto claro, sua unidade, categoria e prioridade.\n3. Descreva o que aconteceu, quando começou e como isso afeta o trabalho. Informe o patrimônio, se houver.\n4. Registre o chamado e guarde o protocolo.\n5. Abra o chamado para acompanhar a situação e as mensagens da equipe de TI.\n\nVocê também pode enviar uma Dúvida / orientação se precisa de uma explicação. Não compartilhe senhas ou dados de cidadãos nas mensagens.",
    },
    {
        "key": "senha-esquecida", "category": "Criação de usuários", "featured": True,
        "title": "Esqueci minha senha. Como solicitar ajuda?",
        "summary": "Saiba a quem recorrer para recuperar o acesso sem compartilhar sua senha.",
        "body": "Se você consegue entrar no Service Desk e esqueceu a senha de outro sistema, abra um chamado na categoria Criação de usuários. Informe o sistema, seu usuário e a unidade. Não escreva sua senha atual nem uma senha desejada.\n\nSe esqueceu a senha do próprio Service Desk, entre em contato com o responsável de TI da sua unidade por um canal institucional já conhecido. O administrador poderá redefinir sua senha. Não há recuperação automática por e-mail nesta versão.\n\nPara trocar a senha do Service Desk enquanto está conectado, abra o menu da sua conta e escolha Alterar senha.",
    },
    {
        "key": "impressora-nao-imprime", "category": "Impressoras", "featured": True,
        "title": "O que verificar quando a impressora não imprime?",
        "summary": "Faça verificações simples e informe os detalhes certos ao pedir atendimento.",
        "body": "1. Verifique se a impressora está ligada e com papel.\n2. Confira se o painel mostra erro, falta de toner ou papel preso. Não desmonte o equipamento.\n3. Confira se escolheu a impressora correta ao imprimir.\n4. Veja se outras pessoas da unidade também estão com o problema.\n\nSe a falha continuar, abra um chamado em Impressoras. Informe o patrimônio ou nome da impressora, a mensagem exibida e se outras pessoas foram afetadas. Não anexe ou transcreva documentos com dados pessoais para demonstrar a falha.",
    },
    {
        "key": "sem-acesso-rede", "category": "Conectividade", "featured": False,
        "title": "Estou sem acesso à rede. O que posso verificar?",
        "summary": "Identifique se a dificuldade afeta apenas seu computador ou toda a unidade.",
        "body": "Verifique se o cabo de rede está conectado ou se o Wi-Fi institucional está habilitado. Confira com os colegas se eles também perderam o acesso. Anote se a falha ocorre em todos os sistemas ou em apenas um.\n\nNão altere configurações de rede, não reinicie equipamentos compartilhados e não tente contornar os controles de acesso.\n\nAbra um chamado em Conectividade e informe a unidade, os sistemas afetados, o horário de início e o número aproximado de pessoas impactadas. Se o Service Desk também estiver inacessível, use o canal institucional de contingência da sua unidade.",
    },
    {
        "key": "nova-conta-acesso", "category": "Criação de usuários", "featured": False,
        "title": "Como solicitar uma nova conta ou acesso a um sistema?",
        "summary": "Reúna as informações necessárias antes de encaminhar a solicitação.",
        "body": "Abra um chamado do tipo Requisição de serviço, na categoria Criação de usuários. Informe a unidade, o sistema necessário, as atividades que serão realizadas e o responsável que autoriza o acesso, conforme os procedimentos da prefeitura.\n\nNão envie senhas nem documentos pessoais completos pelo chamado. Se houver necessidade de informações adicionais, a TI orientará o uso de um canal adequado. A abertura do chamado não concede acesso automaticamente.",
    },
    {
        "key": "confirmar-reabrir", "category": None, "featured": True,
        "title": "Como confirmar uma solução ou reabrir um chamado?",
        "summary": "Finalize o atendimento quando estiver resolvido ou avise que o problema continua.",
        "body": "Quando o chamado estiver Resolvido, leia a solução aplicada e teste o funcionamento na sua unidade.\n\nSe estiver tudo certo, escolha Confirmar solução e encerrar.\nSe o problema persistir, escolha Problema persiste · Reabrir e envie uma mensagem explicando o resultado do teste.\n\nUm chamado já Encerrado também pode ser reaberto pelo solicitante. Ele retorna à triagem e mantém o histórico e as mensagens anteriores. Se for um problema diferente, abra um novo chamado para facilitar o acompanhamento.",
    },
    {
        "key": "prioridade", "category": None, "featured": True,
        "title": "Como escolher a prioridade do chamado?",
        "summary": "Considere o impacto nos serviços e nas pessoas da sua unidade.",
        "body": "Crítica: um serviço essencial está interrompido e precisa de atenção imediata da equipe.\nAlta: várias pessoas ou uma atividade importante estão afetadas.\nMédia: há impacto parcial, mas parte do trabalho pode continuar.\nBaixa: orientação, dúvida ou solicitação sem urgência.\n\nExplique o impacto na descrição. A equipe de TI pode reclassificar a prioridade após a triagem. A classificação organiza o atendimento; esta versão não define prazos automáticos de SLA.",
    },
    {
        "key": "computador-nao-liga", "category": "Hardware", "featured": False,
        "title": "O computador não liga. Como pedir suporte?",
        "summary": "Verifique a alimentação externa e registre o equipamento afetado.",
        "body": "Confira visualmente se os cabos de energia do computador e do monitor estão conectados e se a tomada utilizada tem alimentação. Verifique se há luzes ou mensagens no monitor. Não abra o gabinete nem tente reparar componentes internos.\n\nSe houver cheiro de queimado, aquecimento anormal ou ruídos, interrompa o uso e peça orientação à TI.\n\nAbra um chamado em Hardware por outro dispositivo disponível. Informe patrimônio, unidade, o que acontece ao ligar e o impacto no serviço.",
    },
    {
        "key": "erro-programa", "category": "Software", "featured": False,
        "title": "Um programa apresenta erro. Quais informações devo enviar?",
        "summary": "Ajude a TI a reproduzir a falha sem expor dados sensíveis.",
        "body": "Anote o nome do sistema, a etapa em que o erro aparece, o horário e o texto da mensagem de erro. Informe se o problema acontece sempre e se outros usuários também foram afetados.\n\nAbra um chamado em Software e descreva os passos realizados. Não inclua senhas, dados de pacientes ou documentos de cidadãos. Não instale programas ou atualizações por conta própria para tentar corrigir a falha.",
    },
    {
        "key": "ramal-telefonico", "category": "Telefonia", "featured": False,
        "title": "Meu ramal não funciona. O que informar no chamado?",
        "summary": "Identifique o ramal, o local e o tipo de falha nas ligações.",
        "body": "Confira se o aparelho está conectado e anote o número do ramal e a unidade. Verifique se a dificuldade ocorre em ligações internas, externas ou nas duas situações. Descreva se há falta de sinal, ruído ou interrupções.\n\nAbra um chamado em Telefonia e informe o horário de início e se outros ramais estão afetados. Não altere as configurações da central telefônica ou de equipamentos compartilhados.",
    },
]
