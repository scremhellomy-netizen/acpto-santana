# ACPTO SANTANA — pacote corrigido

Este pacote contém:
- `index.html` com o Ranking de responsáveis ocupando toda a largura, igual às tabelas abaixo.
- `scripts/gerar_dados_dashboard.py` com seleção robusta do Excel operacional e leitura exclusiva da aba `Principal`.
- `data/ordens_santana.json.gz` gerado a partir do Excel atualizado.
- `data/manifest.json` com a validação da geração.
- `ATUALIZAR_DADOS_DASHBOARD.bat`.

Validação desta geração:
- Registros: 25.989
- Unidades: 68.225
- Devoluções = SIM: 323
- Tipos de operação: 35
- Responsáveis: 53
- Transportadoras: 2
- Datas válidas: 25.989
- Aba processada: Principal
- A outra aba oculta não é processada.

Observação:
O GitHub ainda estava com o `manifest.json` antigo (25.968 registros / 68.190 unidades / 321 devoluções). Portanto, o dashboard publicado não poderia refletir o Excel mais recente até que os arquivos de `data` fossem substituídos e commitados.
