# Requisitos derivados do TCC

Documento de referência: *TCC UNIP.docx*, fornecido pelo autor na conversa. O conteúdo foi usado como referência de domínio e escopo, sem copiar o documento acadêmico ou suas imagens para o repositório.

O recorte é uma aplicação interna para administração pública municipal. A primeira versão usa Django/MVT, HTML, CSS e JavaScript, com API Django REST Framework. O banco local é SQLite e o fuso é America/Sao_Paulo.

| Objetivo / requisito do TCC | Entrega nesta versão |
| --- | --- |
| Centralizar incidentes e requisições | Formulário de abertura, protocolo e fila pesquisável |
| Hardware, software, conectividade, impressoras, telefonia e criação de usuários | Seis categorias iniciais editáveis |
| Atender unidades e secretarias municipais | Cadastro de unidades e vínculo ao chamado/perfil |
| Diferenciar usuários e níveis de atendimento | Solicitantes, técnicos, gestores e administrador |
| Abertura, classificação, encaminhamento, atendimento e encerramento | Máquina de transições na camada de serviços, responsável obrigatório e confirmação de solução |
| Histórico, situação e responsáveis | Eventos com autor/data e conversa por chamado |
| Comunicação entre servidores e TI | Mensagens públicas e notas internas restritas à TI |
| Prioridades | Baixa, média, alta e crítica, com orientação de impacto no formulário |
| Análise de tempos de resposta e atendimento | Primeira resposta, resolução, encerramento e médias com amostras |
| Identificar recorrência por categoria, equipamento e unidade | Distribuições, patrimônio textual e relatório de recorrência |
| Interface e comunicação via REST | Templates responsivos e API autenticada com o mesmo escopo de acesso |
| Testes funcionais de caixa-preta | Testes com cliente HTTP para interface, autenticação e API; testes do ciclo de atendimento |
| Acompanhar registros de eventos | Linha do tempo na aplicação e consulta somente leitura no Admin |
| Coletar dados para análise | Exportação CSV com marcos de tempo; indicadores na interface e API |

## Decisões do protótipo a validar com os envolvidos

- Técnicos e gestores acessam todos os chamados; solicitantes acessam apenas os próprios, inclusive se forem da mesma unidade.
- O solicitante escolhe prioridade e unidade na abertura; a equipe de TI pode reclassificá-las.
- As unidades cadastradas inicialmente são exemplos. Não representam organograma oficial.
- O equipamento é um identificador textual opcional; não existe módulo de inventário.
- O encaminhamento é manual para um profissional ativo de TI. Não há distribuição automática.
- A conclusão é registrada pela TI, e o solicitante pode confirmá-la ou reabrir. A TI também pode encerrar após resolver.
- Uma reabertura mantém as mensagens e os eventos. A nova resolução usa o intervalo desde a abertura original.
- Os indicadores são de horas corridas, sem SLA ou pausa por calendário útil.
- Contas são provisionadas pelo administrador, sem cadastro público. Não há envio automático de credenciais.
- Não há serviço externo obrigatório, permitindo operação em rede local após instalação.

## Limites das evidências

Testes funcionais demonstram comportamento do software neste ambiente. A avaliação de ganho de eficiência, satisfação e redução do tempo de atendimento depende de coleta real e comparação com a linha de base descrita no TCC. Não existem dados de pesquisa reais nem integração com sistemas da prefeitura nesta entrega.

## Complementos solicitados após a primeira versão

O autor solicitou complementar a área de chamados e incluir suporte a dúvidas. A entrega acrescenta:

- Tipo de chamado Dúvida / orientação, com as mesmas regras de propriedade, histórico e atendimento.
- Contadores por fila, filtros por tipo e chamados sem responsável e ação de assumir atendimento pela TI.
- Central de ajuda autenticada com busca, categorias e perguntas frequentes.
- Artigos publicados para usuários e rascunhos restritos à equipe de TI.
- Gerenciamento de orientações pela equipe de TI e avaliação de utilidade por usuário.
- Referência ao artigo consultado quando a dúvida é encaminhada ao suporte.

As dez orientações iniciais são conteúdo de apoio editável. Não são normas oficiais da prefeitura. O suporte às dúvidas ocorre pela conversa do chamado, sem chatbot, atendimento em tempo real ou integração externa.
