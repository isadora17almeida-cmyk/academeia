# Alterações implementadas nesta rodada

Esta versão aplica as mudanças solicitadas para continuar o projeto ACADEME.IA.

## Questões
- Questões discursivas passam a usar a mesma camada de IA do projeto, compatível com GroqCloud.
- O formulário aceita texto base, PDF, transcrição salva e material da biblioteca.
- Questões objetivas podem ser respondidas online com alternativas clicáveis.
- Gabarito comentado/corrigido fica disponível em cada questão.

## Resumos
- O modo avançado foi reforçado para produzir resumo explicativo, com exemplos do professor/orientador, pontos de prova, pegadinhas, checklist e conclusão.
- O formulário aceita PDF e vários áudios/vídeos da aula.
- Aulas longas são processadas por blocos para evitar limite de tokens.

## Transcrição
- A transcrição principal remove marcações técnicas como `[Parte 1/143]`.
- A área “Transcrição do professor” mostra somente a fala limpa.
- O resumo da aula fica separado e mais explicativo.

## Biblioteca
- Mostra os 3 últimos materiais em destaque.
- Filtros ficaram mais discretos.
- Estrela de favorito fica amarela quando o item está favoritado.
- Itens continuam com exportação em Word, PDF e TXT.

## Flashcards
- A tela foi reorganizada no estilo Anki.
- Mostra acertos, erros, total revisado e aproveitamento no topo.
- Permite gerar flashcards a partir de PDF, texto/resumo ou material da biblioteca.
- Botões “Acertei” e “Errei” registram desempenho.

## Simulados
- Permite anexar PDF/material como base.
- Simulados recentes agora são clicáveis.
- Cada simulado abre uma tela online de resolução.
- Alternativas podem ser respondidas no próprio site.
- Mostra acertos, erros, nota e gabarito comentado.

## Perfil
- Tela de perfil reorganizada em dados pessoais.
- Curso/área tem mais opções.
- Objetivos mudam conforme o curso escolhido.
- Campo de rotina de estudo/trabalho foi adicionado usando o campo de objetivo existente.
- Foto de perfil continua usando upload de imagem.

## Estética
- O bloco de perfil do topo aparece apenas no dashboard.
- O botão de recolher menu foi movido para perto da marca ACADEME.IA.
- A marca “AI” foi substituída por uma logo em imagem SVG.
- Landing page passou a falar com estudantes de todas as áreas, não só Direito e Medicina.

## Produção
- Mantém Render + Gunicorn + PostgreSQL + GroqCloud.
- `start.sh` permanece como comando simples de inicialização.
- `.python-version` e `runtime.txt` foram definidos para Python 3.12.10.
