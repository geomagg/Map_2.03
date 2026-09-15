# OBN Design (Map_2.03)

Aplicativo desktop em **PyQt5 + PyQGIS** para desenho e QC de aquisição sísmica OBN (Ocean Bottom Node): plotagem de nodes, shots, sail lines, polígonos de área, e cálculo de mapas de fold, azimute e diagramas de rosa offset-azimute.

## Requisitos

- **QGIS** com bindings Python (`qgis.core`, `qgis.gui`) — o app roda como aplicação standalone do QGIS, não como plugin.
- **PyQt5**
- **matplotlib** (opcional, só necessário para o Fold Rose — diagrama polar). Sem ele, o resto do app funciona normal; só o Fold Rose avisa que a lib não está disponível.

## Como rodar

```bash
./map
```
ou
```bash
python3 map
```

O executável `map` chama `Map.py`, que inicializa o ambiente QGIS (`app.initQgis()`) e abre a janela principal (`MainWindow`, em `mapMenu.py`).

## Estrutura de arquivos

| Arquivo | O que é |
|---|---|
| `map` | Script de entrada (chama `Map.py`) |
| `Map.py` | Inicializa QGIS e abre a `MainWindow` |
| `mapMenu.py` | Arquivo principal — toda a UI, menus, cálculos (fold, azimute, fold rose) |
| `map_tool.py` | Ferramentas de mapa customizadas: `ConnectTool` (distância/azimute), `infoTool` (identificar feição), `RectSelectTool` (seleção de área) |
| `info_tool.py` | Versão antiga/duplicada do `infoTool` — não é usada (o app importa de `map_tool.py`); pode ser removida |
| `icons.py` / `icons.qrc` | Recursos Qt (ícones da toolbar) compilados |
| `map.spec` | Spec do PyInstaller, se for gerar um executável empacotado |
| `nodes.txt`, `shots.txt`, `sail.txt`, `grid.txt`, `pol2.txt`, `polshot.txt`/`pol3.txt` | Arquivos de dados (ver formato abaixo) |

## Formato dos arquivos de dados

Arquivos texto delimitados por espaço, com cabeçalho `x y s l`:
```
x y s l
300000.00 500000.00 25 25
300400.00 500000.00 25 26
...
```
- `x`, `y`: coordenadas (CRS fixo no código como **EPSG:31983**)
- `s`, `l`: station/line (usados como atributos, ex. no popup do `infoTool`)

`pol2.txt` e `polshot.txt`/`pol3.txt` seguem o mesmo formato, mas representam os **vértices, em ordem, de um polígono** (ex. contorno da área de nodes/shots) — o app conecta os pontos automaticamente e fecha o polígono.

## O que carrega automaticamente ao abrir

No startup, o app carrega e já **exibe**: `nodes.txt`, `pol2.txt` e `polshot.txt` (com fallback para `pol3.txt` se `polshot.txt` não existir), se estiverem na pasta de onde o app foi executado.

`shots.txt`, `sail.txt` e `grid.txt` **não** são carregados automaticamente — use os menus `Layers > Shape_files` (formato shapefile/ogr) ou `Layers > txtfiles` (formato .txt) para carregá-los manualmente quando precisar.

## Menus

- **Layers** — carregar nodes/shots/sail/grid/polígonos, via shapefile (ogr) ou .txt (delimitado)
- **View** — checkboxes para mostrar/esconder cada camada (nodes, shots, sail, grid, polígonos, raster de batimetria, fold map, azimuth map)
- **Layer Preferences** — cor e tamanho de cada camada (nodes, shots, sail, polígonos), e transparência + legenda de cor para fold/azimuth map
- **Preferences** — cor de fundo do canvas, e **diretório de dados** (pasta padrão dos diálogos "Open file")
- **Computations**:
  - **Fold Map** — mapa de fold (cobertura CMP) por bin, com faixa de offset configurável
  - **Azimuth Map** — azimute médio (circular) por bin
  - **Fold Rose (Azimute)** — diagrama polar offset × azimute (requer matplotlib)
  - **Arquivo CMP** — gera/salva/carrega uma tabela de pares fonte-receptor (midpoint, offset, azimute) em cache, para recalcular fold/azimute/rose em diferentes faixas de offset **sem refazer a busca espacial toda vez**

## Toolbar

- Pan, Zoom in/out/full extent
- **Connect** — clique em dois pontos, mostra distância (km) e azimute entre eles
- **Select Area** — arraste um retângulo no mapa; mostra quantos nodes e shots caem dentro dele
- Info tool — clique numa feição pra ver seus atributos (linha/estação, X/Y)

## Notas técnicas / limitações conhecidas

- O CRS está fixo em **EPSG:31983** no código (URIs de carregamento e camadas de memória) — para outra zona UTM, seria necessário trocar essas strings.
- O cache de CMP (`self.cmp_table`) fica só em memória, a menos que você use "Salvar arquivo CMP"; ele é limitado a um **offset máximo escolhido na hora de gerar** — pedir um offset maior que esse depois faz o app recalcular do zero automaticamente.
- `layer.setOpacity()` é usado para transparência de fold/azimuth map (compatível com QGIS 3.x); versões muito antigas do QGIS podem não ter esse método.
- Os diálogos de "Open file" usam `QFileDialog.DontUseNativeDialog` para respeitar corretamente o "diretório de dados" configurado — o visual do diálogo é o genérico do Qt, não o nativo do sistema operacional.
