# Regras de Preenchimento Automático — Plano de Treino 2026

Este documento contém as diretrizes que devem ser seguidas pela IA ao atualizar o arquivo `Plano_Treino_2026.md`.

## Regras de Integridade
1. **Bloqueio de Colunas (A até J):** Nunca alterar os valores das colunas de "Data" até "Detalhes". Isso inclui: Data, Dia, Treino, Distância, Pace Alvo, Zona e Detalhes. Estes campos representam o planejamento original e devem permanecer intactos.
2. **Campos Editáveis:** Apenas as colunas "Pace Real", "Percepção", "Comentários" e "Avaliação" devem ser preenchidas com os dados do treino realizado.

## Regras de Preenchimento
1. **Pace Real:** Calcular a média das parciais ou usar o valor informado.
2. **Percepção e Comentários:** Inserir dados nestas colunas **apenas se forem explicitamente mencionados** na mensagem do usuário. Caso contrário, deixar em branco.
3. **Avaliação (IA):** Gerar obrigatoriamente uma análise técnica comparando o Pace Real vs. Pace Alvo e a Distância Planejada vs. Distância Real, além de considerar quaisquer dores ou observações relatadas.
