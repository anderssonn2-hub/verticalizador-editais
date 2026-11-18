# V3.0.5 DEV
- Limites do conteúdo por cabeçalho e próximo anexo.
- Perfil estruturado para cargos numerados Analista/Técnico Judiciário; conteúdos comuns, exceções e específicos (padrão TRF4).
- Cronograma tabular e órgão no cabeçalho; cadastro de reserva e remuneração por carreira no perfil testado.
- Mantido caminho legado para PCMG. Revisão manual ainda necessária; escopo manual não altera a seleção estruturada.
- Rollback: restaurar arquivos da V3.0.4 e universal.py anterior; estrutura.py pode ser removido.

# V3.0.6 DEV
- Seleção de cargo por chips; grupos de conteúdo separados no perfil estruturado; páginas automáticas de origem.
- Fallback sem classificação não comprovada.

## V3.0.7 DEV
- OCR automático por página no Raio-X; requer Tesseract com português.
- Seleção por botões em grade e reconhecimento inicial de cabeçalhos TRF.
- Não considera o PDF inteiro como conteúdo quando não há seção detectada.

## V3.0.8 DEV
- Parser experimental de conteúdo com escopo por cargo e cartões expansíveis no Raio-X.
- OCR preservado; exportação não alterada.

## V3.0.9 DEV
- Cronograma com continuidade entre páginas, linhas de eventos e datas em linhas separadas.
- Expressões alternativas de aplicação/realização de provas; exclusão de eventos administrativos.
- Fallback por campo ausente; conteúdo programático e OCR mantidos.

## V3.0.10 DEV
- Cards por cargo, salário e taxa separados, vagas associadas por linhas codificadas.
- Estrutura da prova por código, distribuição somente quando consistente.
- Validação parcial por OCR das páginas 1, 8 e 16; interface e outros formatos pendentes.
