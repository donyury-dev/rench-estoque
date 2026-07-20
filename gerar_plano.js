const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
  TableOfContents
} = require('docx');
const fs = require('fs');

// Colors
const BLUE_DARK   = '1A3A5C';
const BLUE_MID    = '2E6DA4';
const BLUE_LIGHT  = 'D5E8F0';
const BLUE_HEADER = '1F5F8B';
const GRAY_ROW    = 'E8F0F8';
const GREEN_DARK  = '1A6B3A';
const GREEN_LIGHT = 'D6F0E0';
const RED_DARK    = '8B1A1A';
const RED_LIGHT   = 'F8D7DA';
const WHITE       = 'FFFFFF';

const cellBorder = { style: BorderStyle.SINGLE, size: 4, color: BLUE_MID };
const allBorders = { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder };
const noBorder   = { style: BorderStyle.NONE, size: 0, color: WHITE };
const noBorders  = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, bold: true, size: 36, color: BLUE_DARK, font: 'Arial' })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 140 },
    children: [new TextRun({ text, bold: true, size: 28, color: BLUE_HEADER, font: 'Arial' })],
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, bold: true, size: 24, color: BLUE_MID, font: 'Arial' })],
  });
}
function p(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    children: [new TextRun({ text, size: 22, font: 'Arial', ...opts })],
  });
}
function bullet(text) {
  return new Paragraph({
    numbering: { reference: 'bullet-list', level: 0 },
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text, size: 22, font: 'Arial' })],
  });
}
function subBullet(text) {
  return new Paragraph({
    numbering: { reference: 'bullet-list', level: 1 },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, size: 20, font: 'Arial', color: '444444' })],
  });
}
function divider() {
  return new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BLUE_MID } },
    spacing: { before: 160, after: 160 },
    children: [],
  });
}
function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}
function tableHeader(cells, widths) {
  return new TableRow({
    tableHeader: true,
    children: cells.map((text, i) =>
      new TableCell({
        borders: allBorders,
        width: { size: widths[i], type: WidthType.DXA },
        shading: { fill: BLUE_HEADER, type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 100, left: 120, right: 120 },
        verticalAlign: VerticalAlign.CENTER,
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text, bold: true, size: 20, color: WHITE, font: 'Arial' })],
        })],
      })
    ),
  });
}
function tableRow(cells, widths, shade = false) {
  return new TableRow({
    children: cells.map((text, i) =>
      new TableCell({
        borders: allBorders,
        width: { size: widths[i], type: WidthType.DXA },
        shading: { fill: shade ? GRAY_ROW : WHITE, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({
          children: [new TextRun({ text, size: 20, font: 'Arial' })],
        })],
      })
    ),
  });
}

// Linha com celulas coloridas individualmente
function compRow(cells, widths, shade = false) {
  return new TableRow({
    children: cells.map((item, i) => {
      const fill = item.fill || (shade ? GRAY_ROW : WHITE);
      return new TableCell({
        borders: allBorders,
        width: { size: widths[i], type: WidthType.DXA },
        shading: { fill, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({
          alignment: i >= 1 ? AlignmentType.CENTER : AlignmentType.LEFT,
          children: [new TextRun({ text: item.text, size: 19, font: 'Arial', bold: item.bold || false, color: item.color || '000000' })],
        })],
      });
    }),
  });
}

// Bloco padrao de software: cabecalho azul + tabela de 2 colunas
function softwareBlock(nome, site, tipo, pontos, limitacoes) {
  return [
    new Table({
      width: { size: 9026, type: WidthType.DXA },
      columnWidths: [9026],
      rows: [new TableRow({ children: [new TableCell({
        borders: allBorders,
        shading: { fill: BLUE_DARK, type: ShadingType.CLEAR },
        margins: { top: 120, bottom: 120, left: 200, right: 200 },
        width: { size: 9026, type: WidthType.DXA },
        children: [new Paragraph({ children: [
          new TextRun({ text: nome + ' ', bold: true, size: 26, color: WHITE, font: 'Arial' }),
          new TextRun({ text: '\u2013  ' + site, size: 20, color: BLUE_LIGHT, font: 'Arial' }),
        ]})],
      })]})],
    }),
    new Table({
      width: { size: 9026, type: WidthType.DXA },
      columnWidths: [2000, 7026],
      rows: [
        new TableRow({ children: [
          new TableCell({ borders: allBorders, width: { size: 2000, type: WidthType.DXA }, shading: { fill: GRAY_ROW, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: 'Categoria', bold: true, size: 20, font: 'Arial' })] })] }),
          new TableCell({ borders: allBorders, width: { size: 7026, type: WidthType.DXA }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: tipo, size: 20, font: 'Arial' })] })] }),
        ]}),
        new TableRow({ children: [
          new TableCell({ borders: allBorders, width: { size: 2000, type: WidthType.DXA }, shading: { fill: GRAY_ROW, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: 'O que faz bem', bold: true, size: 20, font: 'Arial', color: GREEN_DARK })] })] }),
          new TableCell({ borders: allBorders, width: { size: 7026, type: WidthType.DXA }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: pontos, size: 20, font: 'Arial' })] })] }),
        ]}),
        new TableRow({ children: [
          new TableCell({ borders: allBorders, width: { size: 2000, type: WidthType.DXA }, shading: { fill: GRAY_ROW, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: 'Limita\u00e7\u00f5es para a Rench', bold: true, size: 20, font: 'Arial', color: RED_DARK })] })] }),
          new TableCell({ borders: allBorders, width: { size: 7026, type: WidthType.DXA }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: limitacoes, size: 20, font: 'Arial' })] })] }),
        ]}),
      ],
    }),
    p(''),
  ];
}

// ─── DOCUMENT ───────────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [{
      reference: 'bullet-list',
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: '\u2022', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: '\u25E6', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
      ],
    }],
  },
  styles: {
    default: { document: { run: { font: 'Arial', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 36, bold: true, font: 'Arial', color: BLUE_DARK },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: 'Arial', color: BLUE_HEADER },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 24, bold: true, font: 'Arial', color: BLUE_MID },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1300, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BLUE_MID } },
          spacing: { after: 120 },
          children: [
            new TextRun({ text: 'Rench Solu\u00e7\u00f5es em Tecnologia  |  ', size: 18, color: '666666', font: 'Arial' }),
            new TextRun({ text: 'Plano de Sistema de Controle de Estoque', size: 18, bold: true, color: BLUE_MID, font: 'Arial' }),
          ],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: BLUE_MID } },
          spacing: { before: 80 },
          children: [
            new TextRun({ text: 'P\u00e1gina ', size: 18, color: '666666', font: 'Arial' }),
            new TextRun({ children: [PageNumber.CURRENT], size: 18, color: '666666', font: 'Arial' }),
            new TextRun({ text: ' de ', size: 18, color: '666666', font: 'Arial' }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, color: '666666', font: 'Arial' }),
            new TextRun({ text: '   |   Uso Interno \u2013 Confidencial', size: 18, color: '888888', font: 'Arial' }),
          ],
        })],
      }),
    },
    children: [

      // ── CAPA ────────────────────────────────────────────────────────────
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 1440, after: 200 },
        children: [new TextRun({ text: 'RENCH SOLU\u00c7\u00d5ES EM TECNOLOGIA', bold: true, size: 52, color: BLUE_DARK, font: 'Arial' })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 600 },
        children: [new TextRun({ text: 'Inova\u00e7\u00e3o e Suporte em TI', size: 28, color: BLUE_MID, font: 'Arial', italics: true })],
      }),
      new Table({
        width: { size: 9026, type: WidthType.DXA }, columnWidths: [9026],
        rows: [new TableRow({ children: [new TableCell({
          borders: noBorders, shading: { fill: BLUE_DARK, type: ShadingType.CLEAR },
          margins: { top: 400, bottom: 400, left: 600, right: 600 }, width: { size: 9026, type: WidthType.DXA },
          children: [
            new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'PLANO DE IMPLANTA\u00c7\u00c3O', bold: true, size: 44, color: WHITE, font: 'Arial' })] }),
            new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120 }, children: [new TextRun({ text: 'Sistema de Controle de Estoque e Rastreamento de Equipamentos', size: 26, color: BLUE_LIGHT, font: 'Arial' })] }),
          ],
        })]})],
      }),
      new Paragraph({ spacing: { before: 600, after: 100 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: 'Documento elaborado para aprova\u00e7\u00e3o do projeto', size: 22, color: '555555', font: 'Arial', italics: true })] }),
      new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: 'Vers\u00e3o 1.0  \u2013  Junho de 2026', size: 22, color: '555555', font: 'Arial' })] }),

      pageBreak(),

      // ── SUMÁRIO ─────────────────────────────────────────────────────────
      new TableOfContents('Sum\u00e1rio', { hyperlink: true, headingStyleRange: '1-3' }),

      pageBreak(),

      // ── 1. APRESENTAÇÃO ─────────────────────────────────────────────────
      h1('1. Apresenta\u00e7\u00e3o'),
      p('Este documento descreve o plano completo para desenvolvimento e implanta\u00e7\u00e3o de um Sistema de Controle de Estoque e Rastreamento de Equipamentos customizado para a Rench Solu\u00e7\u00f5es em Tecnologia.'),
      p('A empresa atua no segmento de loca\u00e7\u00e3o e manuten\u00e7\u00e3o de equipamentos de TI, incluindo impressoras, computadores, servidores e etiquetadoras, atendendo a corpora\u00e7\u00f5es e \u00f3rg\u00e3os p\u00fablicos. O volume e a variedade de ativos gerenciados tornam indispens\u00e1vel um sistema robusto, centralizado e f\u00e1cil de usar.'),
      p('O sistema proposto substitui processos manuais (planilhas, cadernos, e-mails) por uma plataforma digital integrada, garantindo visibilidade total do estoque interno e dos equipamentos locados.'),
      divider(),

      // ── 2. DIAGNÓSTICO ───────────────────────────────────────────────────
      h1('2. Diagn\u00f3stico da Situa\u00e7\u00e3o Atual'),
      p('A seguir est\u00e3o os principais problemas operacionais identificados no processo atual de controle de estoque e rastreamento de equipamentos da Rench Solu\u00e7\u00f5es:'),
      bullet('Falta de visibilidade em tempo real sobre quais equipamentos est\u00e3o em estoque, em manuten\u00e7\u00e3o ou locados'),
      bullet('Dificuldade em localizar rapidamente onde um equipamento espec\u00edfico est\u00e1 instalado no cliente'),
      bullet('Controle manual de consumo de insumos (toner, drum, papel fotogr\u00e1fico, tintas) sujeito a erros'),
      bullet('Aus\u00eancia de alertas autom\u00e1ticos para estoque m\u00ednimo, causando falta de pe\u00e7as cr\u00edticas'),
      bullet('Hist\u00f3rico de manuten\u00e7\u00f5es disperso e de dif\u00edcil consulta'),
      bullet('Retrabalho na gera\u00e7\u00e3o de relat\u00f3rios gerenciais e operacionais'),
      bullet('Risco de perda de patrim\u00f4nio por falta de rastreamento adequado dos ativos'),
      bullet('Aus\u00eancia de controle sobre contratos de loca\u00e7\u00e3o e seus prazos de vencimento'),
      bullet('Dificuldade em identificar quais equipamentos demandam mais manuten\u00e7\u00e3o'),
      divider(),

      pageBreak(),

      // ── 3. VISÃO GERAL DO SISTEMA ────────────────────────────────────────
      h1('3. Vis\u00e3o Geral do Sistema'),
      p('O Sistema de Controle de Estoque e Rastreamento \u00e9 uma aplica\u00e7\u00e3o desktop (Windows), com interface gr\u00e1fica moderna e intuitiva, banco de dados local com backup autom\u00e1tico em nuvem, e acesso m\u00f3vel para consultas e atualiza\u00e7\u00f5es em campo.'),
      p('O sistema \u00e9 dividido em dois grandes blocos:'),
      bullet('Estoque Interno \u2013 controle dos insumos e equipamentos guardados no dep\u00f3sito da empresa'),
      bullet('Estoque Externo / Rastreamento \u2013 controle dos equipamentos locados nos clientes'),
      p('Abaixo est\u00e3o todos os m\u00f3dulos funcionais planejados.'),
      divider(),

      // ── 4. REFERÊNCIAS DE MERCADO – SOFTWARES SIMILARES ─────────────────
      pageBreak(),
      h1('4. Refer\u00eancias de Mercado \u2013 Softwares Similares'),
      p('Para embasar este plano, foram analisados os principais softwares do mercado com funcionalidades semelhantes \u00e0s necess\u00e1rias para a Rench Solu\u00e7\u00f5es. A an\u00e1lise demonstra por que uma solu\u00e7\u00e3o customizada \u00e9 a escolha mais adequada para a realidade da empresa.'),

      h2('4.1 Softwares Analisados'),

      // GLPI
      ...softwareBlock(
        'GLPI', 'glpi-project.org',
        'Software livre de gerenciamento de TI (open source)',
        'Invent\u00e1rio de equipamentos de TI, abertura de chamados (helpdesk), controle de contratos, hist\u00f3rico de ativos, popular no Brasil, suporte em portugu\u00eas',
        'Sem controle de estoque f\u00edsico de insumos (toner, drum, tintas); sem gest\u00e3o de loca\u00e7\u00e3o para clientes externos; exige servidor web e configura\u00e7\u00e3o t\u00e9cnica avan\u00e7ada; complexo para usu\u00e1rios sem perfil de TI'
      ),

      // Snipe-IT
      ...softwareBlock(
        'Snipe-IT', 'snipeitapp.com',
        'Gerenciamento de ativos de TI (open source)',
        'Interface f\u00e1cil de usar, rastreamento de equipamentos por n\u00famero de s\u00e9rie, hist\u00f3rico de movimenta\u00e7\u00f5es, gera\u00e7\u00e3o de QR Code e c\u00f3digo de barras, check-in/check-out de equipamentos',
        'Sem controle de estoque de consumíveis (toner, drum, tintas); sem m\u00f3dulo de OS de manuten\u00e7\u00e3o; sem gest\u00e3o de contratos de loca\u00e7\u00e3o; sem alertas autom\u00e1ticos de repostos; interface em ingl\u00eas'
      ),

      // TOTVS
      ...softwareBlock(
        'TOTVS Protheus', 'totvs.com',
        'ERP empresarial completo, amplamente utilizado no Brasil',
        'Controle de estoque, programa\u00e7\u00e3o de ordens de servi\u00e7o, manuten\u00e7\u00e3o de ativos, relat\u00f3rios avan\u00e7ados, amplamente utilizado no mercado brasileiro',
        'Complexidade desproporcional ao porte da empresa; implementa\u00e7\u00e3o longa (6 a 18 meses); n\u00e3o espec\u00edfico para loca\u00e7\u00e3o de equipamentos de TI; requer equipe especializada para opera\u00e7\u00e3o e manuten\u00e7\u00e3o'
      ),

      // Odoo
      ...softwareBlock(
        'Odoo', 'odoo.com',
        'ERP modular open source (antigo OpenERP)',
        'M\u00f3dulo de estoque completo, customiza\u00e7\u00e3o flex\u00edvel, suporte ao portugu\u00eas, integra\u00e7\u00e3o com m\u00f3dulo de compras, comunidade ativa no Brasil',
        'Gen\u00e9rico (voltado ao com\u00e9rcio e varejo); sem rastreamento de equipamentos locados para clientes externos; customiza\u00e7\u00e3o exige desenvolvimento espec\u00edfico; sem controle de OS de manuten\u00e7\u00e3o de TI'
      ),

      pageBreak(),

      // ManageEngine
      ...softwareBlock(
        'ManageEngine AssetExplorer', 'manageengine.com',
        'Software proprietário de gerenciamento de ativos de TI',
        'Invent\u00e1rio detalhado de hardware e software, rastreamento do ciclo de vida do ativo, relat\u00f3rios avan\u00e7ados, controle de garantias, integra\u00e7\u00e3o com helpdesk',
        'Focado em TI interno (n\u00e3o para loca\u00e7\u00e3o a clientes externos); sem controle de consumíveis f\u00edsicos; interface principalmente em ingl\u00eas; n\u00e3o adaptado ao modelo de neg\u00f3cio da Rench'
      ),

      // Freshservice
      ...softwareBlock(
        'Freshservice', 'freshservice.com',
        'Software como Servi\u00e7o (SaaS) para gest\u00e3o de TI',
        'Cat\u00e1logo de ativos, helpdesk avan\u00e7ado, controle de SLA, relat\u00f3rios, boa usabilidade, integra\u00e7\u00f5es com diversas ferramentas de TI',
        'Sem controle de estoque de insumos f\u00edsicos; sem gest\u00e3o de loca\u00e7\u00e3o de equipamentos; dados armazenados em nuvem estrangeira (impacto LGPD); focado em TI corporativo interno'
      ),

      // Bling ERP
      ...softwareBlock(
        'Bling ERP', 'bling.com.br',
        'ERP online voltado a pequenas e m\u00e9dias empresas brasileiras',
        'Controle de estoque e estoque, gest\u00e3o de compras, f\u00e1cil de usar, interface em portugu\u00eas, integra\u00e7\u00e3o com marketplaces',
        'Focado em com\u00e9rcio e varejo; sem rastreamento de equipamentos locados para clientes; sem m\u00f3dulo de OS de manuten\u00e7\u00e3o de TI; sem controle de ativos por n\u00famero de s\u00e9rie ou patrim\u00f4nio'
      ),

      // Lansweeper
      ...softwareBlock(
        'Lansweeper', 'lansweeper.com',
        'Software de descoberta e invent\u00e1rio de rede',
        'Descoberta autom\u00e1tica de dispositivos na rede, invent\u00e1rio detalhado de hardware e software, mapas de rede, identifica\u00e7\u00e3o instant\u00e2nea de equipamentos conectados',
        'Funciona apenas via rede (n\u00e3o rastreia equipamentos f\u00edsicos offline); sem controle de estoque de insumos; sem OS de manuten\u00e7\u00e3o; sem gest\u00e3o de loca\u00e7\u00e3o para clientes externos; interface em ingl\u00eas'
      ),

      h2('4.2 Quadro Comparativo Resumido'),
      // Tabela sem coluna de preco - 6 colunas
      // Widths: 2100 + 1400 + 1400 + 1400 + 1400 + 1326 = 9026
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [2100, 1400, 1400, 1400, 1400, 1326],
        rows: [
          tableHeader(['Software', 'Estoque Insumos', 'Rastr. Loca\u00e7\u00e3o', 'OS Manuten\u00e7\u00e3o', 'Portugu\u00eas', 'Ideal p/ Rench'], [2100, 1400, 1400, 1400, 1400, 1326]),
          compRow([
            { text: 'GLPI' },
            { text: 'Parcial', fill: 'FFF3CD' },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Sim', fill: GREEN_LIGHT, color: GREEN_DARK },
            { text: 'Sim', fill: GREEN_LIGHT, color: GREEN_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
          ], [2100, 1400, 1400, 1400, 1400, 1326], false),
          compRow([
            { text: 'Snipe-IT' },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Parcial', fill: 'FFF3CD' },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Parcial', fill: 'FFF3CD' },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
          ], [2100, 1400, 1400, 1400, 1400, 1326], true),
          compRow([
            { text: 'TOTVS Protheus' },
            { text: 'Sim', fill: GREEN_LIGHT, color: GREEN_DARK },
            { text: 'Parcial', fill: 'FFF3CD' },
            { text: 'Sim', fill: GREEN_LIGHT, color: GREEN_DARK },
            { text: 'Sim', fill: GREEN_LIGHT, color: GREEN_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
          ], [2100, 1400, 1400, 1400, 1400, 1326], false),
          compRow([
            { text: 'Odoo' },
            { text: 'Sim', fill: GREEN_LIGHT, color: GREEN_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Parcial', fill: 'FFF3CD' },
            { text: 'Sim', fill: GREEN_LIGHT, color: GREEN_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
          ], [2100, 1400, 1400, 1400, 1400, 1326], true),
          compRow([
            { text: 'ManageEngine' },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Parcial', fill: 'FFF3CD' },
            { text: 'Parcial', fill: 'FFF3CD' },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
          ], [2100, 1400, 1400, 1400, 1400, 1326], false),
          compRow([
            { text: 'Freshservice' },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Parcial', fill: 'FFF3CD' },
            { text: 'Parcial', fill: 'FFF3CD' },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
          ], [2100, 1400, 1400, 1400, 1400, 1326], true),
          compRow([
            { text: 'Bling ERP' },
            { text: 'Sim', fill: GREEN_LIGHT, color: GREEN_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Sim', fill: GREEN_LIGHT, color: GREEN_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
          ], [2100, 1400, 1400, 1400, 1400, 1326], false),
          compRow([
            { text: 'Lansweeper' },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
            { text: 'Nao', fill: RED_LIGHT, color: RED_DARK },
          ], [2100, 1400, 1400, 1400, 1400, 1326], true),
          // Linha destaque - Sistema Rench
          compRow([
            { text: 'SISTEMA RENCH *', bold: true, color: WHITE, fill: BLUE_HEADER },
            { text: 'SIM', bold: true, color: WHITE, fill: GREEN_DARK },
            { text: 'SIM', bold: true, color: WHITE, fill: GREEN_DARK },
            { text: 'SIM', bold: true, color: WHITE, fill: GREEN_DARK },
            { text: 'SIM', bold: true, color: WHITE, fill: GREEN_DARK },
            { text: 'SIM', bold: true, color: WHITE, fill: GREEN_DARK },
          ], [2100, 1400, 1400, 1400, 1400, 1326], false),
        ],
      }),
      p('* Sistema proposto, desenvolvido sob medida para a Rench Solu\u00e7\u00f5es em Tecnologia', { italics: true, color: '555555' }),

      h2('4.3 Conclus\u00e3o da An\u00e1lise'),
      p('Nenhum dos softwares analisados atende integralmente \u00e0s necessidades da Rench Solu\u00e7\u00f5es. Os ERPs completos (TOTVS, Odoo) t\u00eam complexidade desproporcional ao porte da empresa, enquanto os focados em TI (GLPI, Snipe-IT, ManageEngine, Freshservice) n\u00e3o possuem controle de estoque de insumos f\u00edsicos nem gest\u00e3o de loca\u00e7\u00e3o de equipamentos para clientes externos.'),
      p('Um sistema desenvolvido sob medida \u00e9 a \u00fanica forma de reunir todas as funcionalidades necess\u00e1rias, com linguagem e processos alinhados \u00e0 realidade operacional da Rench.'),
      divider(),

      pageBreak(),

      // ── 5. MÓDULOS ───────────────────────────────────────────────────────
      h1('5. M\u00f3dulos e Funcionalidades'),

      h2('5.1 M\u00f3dulo de Cadastro de Produtos e Equipamentos'),
      p('Centraliza o cat\u00e1logo completo de todos os itens gerenciados pela empresa.'),
      h3('Funcionalidades:'),
      bullet('Cadastro de insumos (toner, drum/fotocondutores, esteira, fusor, coletor, tintas, papel fotogr\u00e1fico)'),
      subBullet('C\u00f3digo interno, descri\u00e7\u00e3o, categoria, marca, modelo compat\u00edvel, fornecedor'),
      subBullet('Foto do produto, c\u00f3digo de barras / QR Code'),
      bullet('Cadastro de equipamentos (impressoras, computadores, servidores, etiquetadoras, monitores, CPUs)'),
      subBullet('N\u00famero de s\u00e9rie \u00fanico, n\u00famero de patrim\u00f4nio, fabricante, modelo, ano de fabrica\u00e7\u00e3o'),
      subBullet('Status atual: em estoque, locado, em manuten\u00e7\u00e3o, descartado'),
      subBullet('Foto do equipamento, manual t\u00e9cnico em PDF vinculado'),
      bullet('Categorias e subcategorias personaliz\u00e1veis'),
      bullet('Vincula\u00e7\u00e3o de insumos compat\u00edveis com cada modelo de equipamento'),
      bullet('Importa\u00e7\u00e3o em lote via planilha Excel (migra\u00e7\u00e3o do controle atual)'),

      h2('5.2 M\u00f3dulo de Controle de Estoque Interno'),
      p('Gerencia a movimenta\u00e7\u00e3o de todos os itens dentro do dep\u00f3sito da empresa.'),
      h3('Funcionalidades:'),
      bullet('Entrada de mercadoria: registro de fornecedores, quantidade, data de recebimento, lote e validade'),
      bullet('Sa\u00edda de mercadoria: consumo interno, envio para cliente, descarte, transfer\u00eancia'),
      bullet('Estoque m\u00ednimo e m\u00e1ximo configur\u00e1vel por produto'),
      bullet('Alertas autom\u00e1ticos visuais e por e-mail quando o estoque atingir o n\u00edvel m\u00ednimo'),
      bullet('Controle de localiza\u00e7\u00e3o f\u00edsica interna: prateleira, corredor, arm\u00e1rio (endere\u00e7amento)'),
      bullet('Invent\u00e1rio f\u00edsico com confer\u00eancia via leitura de c\u00f3digo de barras / QR Code'),
      bullet('Hist\u00f3rico completo de movimenta\u00e7\u00f5es com data, hora, usu\u00e1rio respons\u00e1vel e motivo'),
      bullet('Controle de lotes e validade para itens com vida \u00fatil (tintas, papel fotogr\u00e1fico)'),
      bullet('Dashboard de resumo: total de itens em estoque, itens cr\u00edticos, \u00faltimas movimenta\u00e7\u00f5es'),

      pageBreak(),

      h2('5.3 M\u00f3dulo de Rastreamento de Equipamentos (Estoque Externo)'),
      p('Este \u00e9 o m\u00f3dulo estrat\u00e9gico: permite saber em tempo real onde cada equipamento da empresa est\u00e1 instalado.'),
      h3('Funcionalidades:'),
      bullet('Visualiza\u00e7\u00e3o de localiza\u00e7\u00e3o: exibe onde cada equipamento est\u00e1 (cliente, endere\u00e7o, setor)'),
      bullet('Ficha completa do equipamento locado: cliente, contrato, data de instala\u00e7\u00e3o, t\u00e9cnico respons\u00e1vel'),
      bullet('Busca r\u00e1pida por n\u00famero de s\u00e9rie, patrim\u00f4nio ou nome do cliente'),
      bullet('Hist\u00f3rico de localiza\u00e7\u00f5es: todas as empresas onde o equipamento j\u00e1 esteve'),
      bullet('Controle de data de in\u00edcio e fim de loca\u00e7\u00e3o por equipamento'),
      bullet('Alerta de vencimento de contrato de loca\u00e7\u00e3o (30, 15 e 7 dias antes)'),
      bullet('Registro de transfer\u00eancia entre clientes (desmonta em local A, instala em local B)'),
      bullet('Visualiza\u00e7\u00e3o por cliente: todos os equipamentos locados para uma empresa'),
      bullet('Visualiza\u00e7\u00e3o por equipamento: toda a vida \u00fatil e movimenta\u00e7\u00e3o do ativo'),
      bullet('Etiqueta de identifica\u00e7\u00e3o com QR Code para colagem no equipamento (impress\u00e3o direta)'),

      h2('5.4 M\u00f3dulo de Cadastro de Clientes'),
      p('Base completa das empresas atendidas pela Rench.'),
      h3('Funcionalidades:'),
      bullet('Cadastro com CNPJ/CPF, raz\u00e3o social, endere\u00e7o completo, contatos'),
      bullet('V\u00ednculos com contratos ativos de loca\u00e7\u00e3o e suporte'),
      bullet('Lista de todos os equipamentos locados para o cliente'),
      bullet('Hist\u00f3rico de manuten\u00e7\u00f5es realizadas nos equipamentos do cliente'),
      bullet('Controle de SLA (prazo m\u00e1ximo de atendimento por contrato)'),
      bullet('Anexar documentos: contratos, laudos, fotos de instala\u00e7\u00e3o'),

      h2('5.5 M\u00f3dulo de Ordens de Servi\u00e7o e Manuten\u00e7\u00e3o'),
      p('Gerencia todas as manuten\u00e7\u00f5es preventivas e corretivas nos equipamentos.'),
      h3('Funcionalidades:'),
      bullet('Abertura de OS: cliente, equipamento, problema relatado, t\u00e9cnico designado, prioridade'),
      bullet('Vincula\u00e7\u00e3o autom\u00e1tica com o equipamento e seu hist\u00f3rico de manuten\u00e7\u00f5es anteriores'),
      bullet('Baixa autom\u00e1tica de pe\u00e7as e insumos utilizados na OS (integrado ao estoque interno)'),
      bullet('Registro da solu\u00e7\u00e3o aplicada, pe\u00e7as trocadas, tempo gasto, assinatura do cliente'),
      bullet('Status da OS: aberta, em andamento, aguardando pe\u00e7a, conclu\u00edda, cancelada'),
      bullet('Alerta de OS em atraso ou pr\u00f3ximas do prazo de SLA'),
      bullet('Manuten\u00e7\u00e3o preventiva: agenda autom\u00e1tica baseada em periodicidade ou contador de p\u00e1ginas'),
      bullet('Gera\u00e7\u00e3o de relat\u00f3rio de OS para envio ao cliente em PDF'),
      bullet('Painel t\u00e9cnico: todas as OS do dia, prioridade e rota sugerida'),

      pageBreak(),

      h2('5.6 M\u00f3dulo de Fornecedores e Repostos'),
      p('Otimiza o processo de reposi\u00e7\u00e3o de estoque.'),
      h3('Funcionalidades:'),
      bullet('Cadastro completo de fornecedores com tabela de produtos fornecidos e prazo de entrega'),
      bullet('Sugesto autom\u00e1tica de repostos quando o estoque m\u00ednimo \u00e9 atingido'),
      bullet('Registro de pedidos de compra com acompanhamento de status (solicitado, aprovado, recebido)'),
      bullet('Hist\u00f3rico de fornecimentos por fornecedor'),
      bullet('Acompanhamento de entradas vinculadas ao pedido'),
      bullet('Indicador de desempenho do fornecedor (pontualidade e qualidade das entregas)'),

      h2('5.7 M\u00f3dulo de Relat\u00f3rios e Dashboard Gerencial'),
      p('Transforma os dados do sistema em informa\u00e7\u00e3o estrat\u00e9gica para tomada de decis\u00e3o.'),
      h3('Relat\u00f3rios Operacionais:'),
      bullet('Posi\u00e7\u00e3o de estoque atual (quantidade por produto)'),
      bullet('Movimenta\u00e7\u00f5es por per\u00edodo (entradas, sa\u00eddas, ajustes)'),
      bullet('Itens abaixo do estoque m\u00ednimo (lista de repostos sugerida)'),
      bullet('Equipamentos por cliente e por localiza\u00e7\u00e3o'),
      bullet('OS abertas, conclu\u00eddas e em atraso por per\u00edodo'),
      bullet('Pe\u00e7as mais consumidas por equipamento e por modelo'),
      h3('Relat\u00f3rios Gerenciais:'),
      bullet('Volume de manuten\u00e7\u00f5es por cliente e por equipamento'),
      bullet('Quantidade total de ativos (estoque interno + equipamentos locados)'),
      bullet('Giro de estoque: itens que mais saem e itens parados'),
      bullet('Indicadores de desempenho (KPIs): tempo m\u00e9dio de atendimento, taxa de reabertura de OS'),
      bullet('Gr\u00e1fico de consumo mensal de insumos'),
      h3('Exporta\u00e7\u00e3o:'),
      bullet('PDF, Excel e CSV para todos os relat\u00f3rios'),
      bullet('Envio autom\u00e1tico por e-mail (mensal, semanal ou sob demanda)'),

      h2('5.8 M\u00f3dulo de Alertas e Notifica\u00e7\u00f5es'),
      bullet('Estoque m\u00ednimo atingido: alerta visual no sistema e e-mail para o respons\u00e1vel'),
      bullet('Contrato de loca\u00e7\u00e3o pr\u00f3ximo do vencimento (30, 15 e 7 dias antes)'),
      bullet('Manuten\u00e7\u00e3o preventiva agendada pr\u00f3xima da data'),
      bullet('OS em atraso ou com prazo cr\u00edtico de SLA'),
      bullet('Equipamento com alto volume de manuten\u00e7\u00f5es (candidato a substitui\u00e7\u00e3o)'),
      bullet('Pe\u00e7a ou insumo com validade pr\u00f3xima do vencimento'),

      pageBreak(),

      h2('5.9 M\u00f3dulo de Usu\u00e1rios e Seguran\u00e7a de Acesso'),
      bullet('Cadastro de usu\u00e1rios com n\u00edveis de permiss\u00e3o (Administrador, Gerente, T\u00e9cnico, Somente Leitura)'),
      bullet('Login com senha criptografada'),
      bullet('Registro de auditoria: cada a\u00e7\u00e3o registra data, hora e usu\u00e1rio respons\u00e1vel'),
      bullet('T\u00e9cnico de campo: acesso mobile para atualizar OS e movimentar estoque em tempo real'),
      bullet('Backup autom\u00e1tico di\u00e1rio do banco de dados'),
      bullet('Restaura\u00e7\u00e3o de backup com poucos cliques'),

      h2('5.10 M\u00f3dulo de Leitura de C\u00f3digo de Barras / QR Code'),
      bullet('Integra\u00e7\u00e3o com leitor de c\u00f3digo de barras USB (plug-and-play)'),
      bullet('Leitura via c\u00e2mera do smartphone para uso em campo'),
      bullet('Entrada e sa\u00edda de estoque por leitura: agilidade no almoxarifado'),
      bullet('Identifica\u00e7\u00e3o instant\u00e2nea do equipamento ao escanear a etiqueta'),
      bullet('Gera\u00e7\u00e3o e impress\u00e3o de etiquetas com QR Code em impressoras t\u00e9rmicas ou a laser'),

      divider(),

      // ── 6. QUADRO RESUMO ─────────────────────────────────────────────────
      h1('6. Quadro Resumo dos M\u00f3dulos'),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [3200, 3700, 2126],
        rows: [
          tableHeader(['M\u00f3dulo', 'Principal Benef\u00edcio', 'P\u00fablico-Alvo'], [3200, 3700, 2126]),
          tableRow(['Cadastro de Produtos', 'Cat\u00e1logo \u00fanico e padronizado', 'Almoxarife / TI'], [3200, 3700, 2126], false),
          tableRow(['Estoque Interno', 'Controle em tempo real + alertas', 'Almoxarife / Compras'], [3200, 3700, 2126], true),
          tableRow(['Rastreamento Externo', 'Localizar equipamento em segundos', 'Gerente / T\u00e9cnico'], [3200, 3700, 2126], false),
          tableRow(['Clientes', 'Vis\u00e3o 360\u00ba do cliente', 'Comercial / Suporte'], [3200, 3700, 2126], true),
          tableRow(['OS e Manuten\u00e7\u00e3o', 'Agilidade e rastreabilidade do servi\u00e7o', 'T\u00e9cnico / Gerente'], [3200, 3700, 2126], false),
          tableRow(['Fornecedores', 'Controle de repostos e entregas', 'Compras'], [3200, 3700, 2126], true),
          tableRow(['Relat\u00f3rios e Dashboard', 'Decis\u00f5es baseadas em dados', 'Dire\u00e7\u00e3o / Gest\u00e3o'], [3200, 3700, 2126], false),
          tableRow(['Alertas', 'Preven\u00e7\u00e3o de faltas e atrasos', 'Todos'], [3200, 3700, 2126], true),
          tableRow(['Usu\u00e1rios e Seguran\u00e7a', 'Controle de acesso e auditoria', 'TI / Dire\u00e7\u00e3o'], [3200, 3700, 2126], false),
          tableRow(['QR Code / Cod. Barras', 'Agilidade operacional no campo', 'T\u00e9cnico / Almoxarife'], [3200, 3700, 2126], true),
        ],
      }),

      divider(),
      pageBreak(),

      // ── 7. ESPECIFICAÇÃO TÉCNICA ─────────────────────────────────────────
      h1('7. Especifica\u00e7\u00e3o T\u00e9cnica'),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [3000, 6026],
        rows: [
          tableHeader(['Componente', 'Especifica\u00e7\u00e3o'], [3000, 6026]),
          tableRow(['Plataforma', 'Aplica\u00e7\u00e3o Desktop Windows (10/11) + App Mobile Android'], [3000, 6026], false),
          tableRow(['Banco de Dados', 'PostgreSQL local com sincroniza\u00e7\u00e3o opcional em nuvem'], [3000, 6026], true),
          tableRow(['Interface', 'Interface gr\u00e1fica moderna, responsiva e em portugu\u00eas'], [3000, 6026], false),
          tableRow(['Leitor de c\u00f3digo', 'USB HID (qualquer leitor padr\u00e3o) + c\u00e2mera mobile'], [3000, 6026], true),
          tableRow(['Backup', 'Autom\u00e1tico di\u00e1rio local + backup em nuvem (Google Drive / OneDrive)'], [3000, 6026], false),
          tableRow(['Relat\u00f3rios', 'Exporta\u00e7\u00e3o em PDF, Excel e CSV'], [3000, 6026], true),
          tableRow(['Notifica\u00e7\u00f5es', 'E-mail autom\u00e1tico + alertas visuais no sistema'], [3000, 6026], false),
          tableRow(['Seguran\u00e7a', 'Autentica\u00e7\u00e3o por senha + criptografia do banco de dados'], [3000, 6026], true),
          tableRow(['Escalabilidade', 'Suporte a m\u00faltiplos computadores em rede local (LAN)'], [3000, 6026], false),
        ],
      }),
      divider(),

      // ── 8. BENEFÍCIOS ESPERADOS ──────────────────────────────────────────
      h1('8. Benef\u00edcios Esperados'),
      h2('8.1 Operacionais'),
      bullet('Redu\u00e7\u00e3o do tempo de localiza\u00e7\u00e3o de equipamentos locados'),
      bullet('Elimina\u00e7\u00e3o de rupturas de estoque de insumos cr\u00edticos'),
      bullet('Redu\u00e7\u00e3o do tempo de abertura e fechamento de OS'),
      bullet('Padroniza\u00e7\u00e3o dos processos internos de controle'),
      bullet('Elimina\u00e7\u00e3o de planilhas manuais e e-mails de controle'),
      bullet('Rastreabilidade completa de cada equipamento ao longo de sua vida \u00fatil'),
      h2('8.2 Estrat\u00e9gicos'),
      bullet('Profissionaliza\u00e7\u00e3o da opera\u00e7\u00e3o da Rench Solu\u00e7\u00f5es'),
      bullet('Dados confi\u00e1veis para decis\u00f5es gerenciais'),
      bullet('Melhor qualidade de atendimento ao cliente com controle rigoroso de SLA'),
      bullet('Crescimento sustent\u00e1vel: sistema escal\u00e1vel para novos clientes e equipamentos'),
      bullet('Redu\u00e7\u00e3o de perdas por falta de rastreamento adequado'),
      bullet('Identifica\u00e7\u00e3o de equipamentos com alto volume de manuten\u00e7\u00f5es (candidatos a substitui\u00e7\u00e3o)'),
      divider(),

      pageBreak(),

      // ── 9. FASES DE IMPLANTAÇÃO ──────────────────────────────────────────
      h1('9. Fases de Implanta\u00e7\u00e3o'),
      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [1200, 2200, 3826, 1800],
        rows: [
          tableHeader(['Fase', 'Nome', 'Atividades', 'Dura\u00e7\u00e3o'], [1200, 2200, 3826, 1800]),
          tableRow(['1', 'Levantamento', 'Mapear todos os equipamentos, insumos, clientes e fluxos atuais', '2 semanas'], [1200, 2200, 3826, 1800], false),
          tableRow(['2', 'Desenvolvimento', 'Desenvolvimento do sistema conforme especifica\u00e7\u00f5es deste plano', '8\u201312 semanas'], [1200, 2200, 3826, 1800], true),
          tableRow(['3', 'Migra\u00e7\u00e3o de Dados', 'Importa\u00e7\u00e3o das planilhas e dados existentes para o sistema', '1\u20132 semanas'], [1200, 2200, 3826, 1800], false),
          tableRow(['4', 'Treinamento', 'Capacita\u00e7\u00e3o da equipe (almoxarife, t\u00e9cnicos, gestores)', '1 semana'], [1200, 2200, 3826, 1800], true),
          tableRow(['5', 'Opera\u00e7\u00e3o Assistida', 'Uso real com acompanhamento e ajustes finos', '2 semanas'], [1200, 2200, 3826, 1800], false),
          tableRow(['6', 'Produ\u00e7\u00e3o Plena', 'Sistema em opera\u00e7\u00e3o com suporte mensal incluso', 'Cont\u00ednuo'], [1200, 2200, 3826, 1800], true),
        ],
      }),
      divider(),

      // ── 10. CONCLUSÃO ────────────────────────────────────────────────────
      h1('10. Conclus\u00e3o e Solicita\u00e7\u00e3o de Aprova\u00e7\u00e3o'),
      p('O Sistema de Controle de Estoque e Rastreamento de Equipamentos representa um investimento estrat\u00e9gico na infraestrutura operacional da Rench Solu\u00e7\u00f5es em Tecnologia.'),
      p('Como demonstrado na an\u00e1lise de mercado (Se\u00e7\u00e3o 4), nenhum software existente atende completamente \u00e0s necessidades espec\u00edficas da empresa. O sistema customizado proposto entrega todos os recursos necess\u00e1rios, no idioma correto, com processos adequados ao segmento de loca\u00e7\u00e3o e manuten\u00e7\u00e3o de equipamentos de TI.'),
      p('Com este sistema, a empresa passar\u00e1 a operar com:'),
      bullet('Visibilidade completa e em tempo real de todos os ativos (internos e externos)'),
      bullet('Processos padronizados e audit\u00e1veis'),
      bullet('Maior satisfa\u00e7\u00e3o dos clientes pelo controle rigoroso de SLA'),
      bullet('Informa\u00e7\u00f5es precisas para decis\u00f5es de gest\u00e3o e crescimento sustent\u00e1vel'),
      p(''),
      p('Solicitamos a aprova\u00e7\u00e3o para darmos in\u00edcio \u00e0 Fase 1 \u2013 Levantamento, com prazo estimado de entrega do sistema funcional em at\u00e9 14 semanas ap\u00f3s a aprova\u00e7\u00e3o.', { bold: true }),
      p(''),
      new Table({
        width: { size: 9026, type: WidthType.DXA }, columnWidths: [9026],
        rows: [new TableRow({ children: [new TableCell({
          borders: allBorders, shading: { fill: BLUE_LIGHT, type: ShadingType.CLEAR },
          margins: { top: 200, bottom: 200, left: 400, right: 400 }, width: { size: 9026, type: WidthType.DXA },
          children: [
            new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '"Controlar \u00e9 crescer com seguran\u00e7a."', size: 24, italics: true, color: BLUE_DARK, font: 'Arial' })] }),
            new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80 }, children: [new TextRun({ text: 'Rench Solu\u00e7\u00f5es em Tecnologia', size: 20, bold: true, color: BLUE_MID, font: 'Arial' })] }),
          ],
        })]})],
      }),

      new Paragraph({ spacing: { before: 600, after: 100 }, children: [new TextRun({ text: 'Elaborado por: ___________________________________', size: 22, font: 'Arial' })] }),
      new Paragraph({ spacing: { before: 200, after: 100 }, children: [new TextRun({ text: 'Cargo: ___________________________________________', size: 22, font: 'Arial' })] }),
      new Paragraph({ spacing: { before: 200, after: 100 }, children: [new TextRun({ text: 'Data: ____________________________________________', size: 22, font: 'Arial' })] }),
      new Paragraph({ spacing: { before: 400, after: 100 }, children: [new TextRun({ text: 'Aprovado por: ____________________________________', size: 22, font: 'Arial' })] }),
      new Paragraph({ spacing: { before: 200, after: 100 }, children: [new TextRun({ text: 'Data: ____________________________________________', size: 22, font: 'Arial' })] }),

    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('Plano_Sistema_Estoque_Rench.docx', buffer);
  console.log('Documento gerado com sucesso!');
});
