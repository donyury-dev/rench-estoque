const fs = require('fs');
const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  AlignmentType,
  LevelFormat,
  HeadingLevel,
  BorderStyle,
} = require('docx');

const ACCENT = '1F3864'; // azul marinho, moderno e sóbrio
const GRAY = '595959';

const FONT = 'Calibri';

// ---------- Helpers ----------

function sectionHeading(text) {
  return new Paragraph({
    spacing: { before: 260, after: 120 },
    border: {
      bottom: { color: ACCENT, space: 2, style: BorderStyle.SINGLE, size: 6 },
    },
    children: [
      new TextRun({
        text: text.toUpperCase(),
        bold: true,
        color: ACCENT,
        font: FONT,
        size: 22, // 11pt
      }),
    ],
  });
}

function bodyText(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 160, line: 276 },
    children: [
      new TextRun({
        text,
        font: FONT,
        size: 21, // 10.5pt
        color: '262626',
        italics: opts.italics ?? false,
      }),
    ],
  });
}

function bullet(text) {
  return new Paragraph({
    numbering: { reference: 'bullet-list', level: 0 },
    spacing: { after: 60, line: 264 },
    children: [
      new TextRun({
        text,
        font: FONT,
        size: 21,
        color: '262626',
      }),
    ],
  });
}

function jobHeader(cargo, empresa, periodo) {
  return new Paragraph({
    spacing: { before: 140, after: 40 },
    tabStops: [{ type: 'right', position: 9360 }],
    children: [
      new TextRun({ text: `${cargo} — ${empresa}`, bold: true, font: FONT, size: 21, color: '262626' }),
      new TextRun({ text: `\t${periodo}`, font: FONT, size: 20, color: GRAY, italics: true }),
    ],
  });
}

// ---------- Document ----------

const doc = new Document({
  numbering: {
    config: [
      {
        reference: 'bullet-list',
        levels: [
          {
            level: 0,
            format: LevelFormat.BULLET,
            text: '\u2022',
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 320, hanging: 200 } } },
          },
        ],
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: FONT, size: 21 } },
    },
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838 }, // A4
          margin: { top: 900, right: 1080, bottom: 900, left: 1080 },
        },
      },
      children: [
        // Nome
        new Paragraph({
          spacing: { after: 40 },
          children: [
            new TextRun({
              text: 'Sara Victória Santiago Albino',
              bold: true,
              font: FONT,
              size: 40, // 20pt
              color: ACCENT,
            }),
          ],
        }),
        // Título / posicionamento
        new Paragraph({
          spacing: { after: 100 },
          children: [
            new TextRun({
              text: 'Candidata a Jovem Aprendiz | Atendimento ao Cliente e Vendas',
              font: FONT,
              size: 23,
              color: '404040',
              italics: true,
            }),
          ],
        }),
        // Contato
        new Paragraph({
          spacing: { after: 60 },
          border: { bottom: { color: ACCENT, space: 6, style: BorderStyle.SINGLE, size: 10 } },
          children: [
            new TextRun({
              text: '17 anos  |  Rua Andrea Sansovino, 122A  |  (11) 98953-6672  |  sara77809589@gmail.com',
              font: FONT,
              size: 19,
              color: GRAY,
            }),
          ],
        }),

        // OBJETIVO
        sectionHeading('Objetivo'),
        bodyText(
          'Estudante do Ensino Médio em busca da primeira oportunidade profissional como Jovem Aprendiz, com interesse nas áreas de atendimento ao cliente, vendas, telemarketing e operações de loja/fast-food (ex.: McDonald\u2019s). Comunicativa, proativa, ágil e com experiência prática em atendimento ao público. Disponibilidade para trabalhar no período da tarde.'
        ),

        // FORMAÇÃO ACADÊMICA
        sectionHeading('Formação Acadêmica'),
        new Paragraph({
          spacing: { after: 20 },
          children: [
            new TextRun({ text: 'Ensino Médio — Cursando', bold: true, font: FONT, size: 21, color: '262626' }),
          ],
        }),
        bodyText('Colégio Estadual Alberto Conte', { after: 160 }),

        // EXPERIÊNCIA PROFISSIONAL
        sectionHeading('Experiência Profissional'),

        jobHeader('Atendente e Repositora', 'm@cedos', 'Maio/2025 – Janeiro/2026'),
        bullet('Atendimento direto ao cliente, auxiliando na escolha de produtos e esclarecendo dúvidas.'),
        bullet('Reposição e organização de mercadorias nas prateleiras, seguindo os padrões da loja.'),
        bullet('Contribuição para um ambiente de trabalho organizado, com pontualidade e responsabilidade.'),

        jobHeader('Balconista', 'Lígia Bronze', 'Janeiro/2024 – Janeiro/2025'),
        bullet('Atendimento ao público no balcão, com agilidade, cordialidade e boa comunicação.'),
        bullet('Apoio em vendas e conferência de caixa.'),
        bullet('Organização da vitrine e do espaço de atendimento ao cliente.'),

        // HABILIDADES E COMPETÊNCIAS
        sectionHeading('Habilidades e Competências'),
        bullet('Atendimento ao Cliente e Relacionamento Interpessoal'),
        bullet('Comunicação Clara e Objetiva'),
        bullet('Trabalho em Equipe'),
        bullet('Proatividade e Agilidade'),
        bullet('Organização e Pontualidade'),
        bullet('Interesse em Vendas e Telemarketing'),

        // INFORMAÇÕES ADICIONAIS
        sectionHeading('Informações Adicionais'),
        bullet('Disponibilidade para o período da tarde'),
        bullet('Interesse em vaga de Jovem Aprendiz (possível cadastro em programa de aprendizagem)'),
        bullet('Dedicada, responsável, pontual e comunicativa'),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync('Curriculo_Sara_Victoria_Albino.docx', buffer);
  console.log('OK: docx gerado');
});
