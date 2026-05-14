import type { RouteSheet } from "../types/routeSheet";

const PAGE_WIDTH = 842;
const PAGE_HEIGHT = 595;
const MARGIN = 18;
const INNER_MARGIN = 18;
const TOP_STAMP_HEIGHT = 86;
const BOTTOM_STAMP_HEIGHT = 54;

function escapePdfText(text: string) {
  return text.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function truncateMiddle(value: string, max = 28) {
  if (value.length <= max) {
    return value;
  }

  return `${value.slice(0, Math.floor(max / 2) - 2)}...${value.slice(-(Math.floor(max / 2) - 1))}`;
}

function wrapText(text: string, maxLength: number) {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length <= maxLength) {
      current = next;
    } else {
      if (current) {
        lines.push(current);
      }
      current = word;
    }
  }

  if (current) {
    lines.push(current);
  }

  return lines.length > 0 ? lines : [text];
}

function line(x1: number, y1: number, x2: number, y2: number) {
  return `${x1} ${y1} m ${x2} ${y2} l S`;
}

function rect(x: number, y: number, width: number, height: number) {
  return `${x} ${y} ${width} ${height} re S`;
}

function text(x: number, y: number, value: string, font = "F1", size = 12) {
  return `BT /${font} ${size} Tf 1 0 0 1 ${x} ${y} Tm (${escapePdfText(value)}) Tj ET`;
}

function centeredText(pageWidth: number, y: number, value: string, font = "F1", size = 12) {
  const approximateWidth = value.length * size * 0.45;
  const x = Math.max(MARGIN + 6, pageWidth / 2 - approximateWidth / 2);
  return text(x, y, value, font, size);
}

function drawCommonFrame() {
  const outerX = MARGIN;
  const outerY = MARGIN;
  const outerW = PAGE_WIDTH - MARGIN * 2;
  const outerH = PAGE_HEIGHT - MARGIN * 2;

  const innerX = outerX + INNER_MARGIN;
  const innerY = outerY + INNER_MARGIN;
  const innerW = outerW - INNER_MARGIN * 2;
  const innerH = outerH - INNER_MARGIN * 2;

  const topY = innerY + innerH - TOP_STAMP_HEIGHT;
  const bottomY = innerY + BOTTOM_STAMP_HEIGHT;

  const commands = [
    "0.6 w",
    rect(outerX, outerY, outerW, outerH),
    rect(innerX, innerY, innerW, innerH),
    line(innerX, topY, innerX + innerW, topY),
    line(innerX, bottomY, innerX + innerW, bottomY),
  ];

  return {
    commands,
    innerX,
    innerY,
    innerW,
    innerH,
    topY,
    bottomY,
  };
}

function drawTopStamp(fileName: string, productName: string) {
  const { commands, innerX, innerW, innerH, topY } = drawCommonFrame();
  const stampTop = innerY(innerH) - 0;
  void stampTop;
  const leftWidth = 118;
  const rightWidth = 110;
  const centerX = innerX + leftWidth;
  const centerW = innerW - leftWidth - rightWidth;
  const rightX = innerX + innerW - rightWidth;
  const stampBottom = topY;
  const stampTopY = innerY(innerH) ;
  return { commands, innerX, innerW, innerH, topY, leftWidth, rightWidth, centerX, centerW, rightX, stampBottom, stampTopY, fileName, productName };
}

function innerY(innerH: number) {
  return MARGIN + INNER_MARGIN + innerH;
}

function buildCoverPage(routeSheet: RouteSheet) {
  const frame = drawCommonFrame();
  const { commands, innerX, innerY, innerW, innerH, topY } = frame;
  const topStampTop = innerY + innerH;
  const leftWidth = 118;
  const rightWidth = 110;
  const centerX = innerX + leftWidth;
  const centerW = innerW - leftWidth - rightWidth;
  const rightX = innerX + innerW - rightWidth;
  const halfTop = topY + TOP_STAMP_HEIGHT / 2;
  const rowHeight = TOP_STAMP_HEIGHT / 3;

  commands.push(
    line(innerX + leftWidth, topY, innerX + leftWidth, topStampTop),
    line(rightX, topY, rightX, topStampTop),
    line(centerX, halfTop, centerX + centerW, halfTop),
    line(innerX, topY + rowHeight, innerX + leftWidth, topY + rowHeight),
    line(innerX, topY + rowHeight * 2, innerX + leftWidth, topY + rowHeight * 2),
    line(rightX, topY + rowHeight, innerX + innerW, topY + rowHeight),
    line(rightX, topY + rowHeight * 2, innerX + innerW, topY + rowHeight * 2),
      text(innerX + 42, topY + rowHeight * 2 + 9, "Lit.", "F1", 11),
      text(innerX + 24, topY + 9, "Scale", "F1", 11),
      centeredText(PAGE_WIDTH, topY + 16, truncateMiddle(routeSheet["File name"].replace(/\.[^.]+$/, ""), 30), "F2", 18),
      text(rightX + 42, topY + rowHeight * 2 + 9, "14", "F2", 12),
      text(rightX + 48, topY + 9, "1", "F2", 12),
      centeredText(PAGE_WIDTH, innerY + 225, "DOCUMENT PACKAGE", "F2", 24),
      centeredText(PAGE_WIDTH, innerY + 190, "for the manufacturing process of the part", "F2", 18),
    );

  commands.push(...drawBottomStamp("TL", "Title page", truncateMiddle(routeSheet["File name"], 24), "Sheet 1", frame));

  return commands.join("\n");
}

function drawBottomStamp(
  shortCode: string,
  label: string,
  metaLeft: string,
  metaRight: string,
  frame: ReturnType<typeof drawCommonFrame>
) {
  const { innerX, innerY, innerW } = frame;
  const y = innerY;
  const h = BOTTOM_STAMP_HEIGHT;
  const leftW = innerW * 0.58;
  const rightW = innerW - leftW;
  const codeW = 72;
  const pageW = 74;

  return [
    line(innerX + leftW, y, innerX + leftW, y + h),
    line(innerX + codeW, y, innerX + codeW, y + h),
    line(innerX + leftW + (rightW - pageW), y, innerX + leftW + (rightW - pageW), y + h),
    text(innerX + 28, y + 18, shortCode, "F2", 12),
    text(innerX + codeW + 10, y + 18, label, "F1", 12),
    text(innerX + leftW + 10, y + 18, metaLeft, "F1", 12),
    text(innerX + leftW + rightW - pageW + 18, y + 18, metaRight, "F2", 12),
  ];
}

function buildStepsPages(routeSheet: RouteSheet) {
  const frame = drawCommonFrame();
  const { innerX, innerY, innerW, topY, bottomY } = frame;
  const pages: string[] = [];
  const headerHeight = 54;
  const tableTop = topY - headerHeight;
  const pageTitleBottom = topY;
  const columnHeaderHeight = 30;
  const bodyTop = tableTop - columnHeaderHeight;
  const stepAreaHeight = bodyTop - bottomY;
  const rowHeight = 28;
  const rowsPerPage = Math.max(1, Math.floor((stepAreaHeight - 12) / rowHeight) - 1);
  const chunks: typeof routeSheet.Steps[] = [];

  for (let index = 0; index < routeSheet.Steps.length; index += rowsPerPage) {
    chunks.push(routeSheet.Steps.slice(index, index + rowsPerPage));
  }

  chunks.forEach((chunk, pageIndex) => {
    const commands = [...frame.commands];
    const leftCol = 82;
    const actionCol = 230;
    const equipmentCol = 245;
    const x1 = innerX + leftCol;
    const x2 = x1 + actionCol;
    const x3 = x2 + equipmentCol;

    commands.push(
      line(innerX, tableTop, innerX + innerW, tableTop),
      line(innerX, bodyTop, innerX + innerW, bodyTop),
      line(x1, bottomY, x1, pageTitleBottom),
      line(x2, bottomY, x2, pageTitleBottom),
      line(x3, bottomY, x3, pageTitleBottom),
      text(innerX + 18, topY - 32, "Document", "F1", 12),
      text(innerX + 18, topY - 48, "Route sheet", "F2", 14),
      text(innerX + innerW / 2 + 16, topY - 32, "Part", "F1", 12),
      text(innerX + innerW / 2 + 16, topY - 48, truncateMiddle(routeSheet["File name"].replace(/\.[^.]+$/, ""), 28), "F2", 14),
      text(innerX + 26, bodyTop + 9, "Step", "F2", 11),
      text(x1 + 18, bodyTop + 9, "Action", "F2", 11),
      text(x2 + 18, bodyTop + 9, "Equipment", "F2", 11),
      text(x3 + 18, bodyTop + 9, "ISO", "F2", 11),
    );

    let currentY = bodyTop - rowHeight;
    chunk.forEach((step) => {
      commands.push(line(innerX, currentY, innerX + innerW, currentY));

      const action = wrapText(step.Action, 26)[0] || "";
      const equipment = wrapText(step.Equipment.join(", "), 28)[0] || "";
      const iso = wrapText(step.ISO.join(", "), 20)[0] || "";

      commands.push(
        text(innerX + 24, currentY + 7, String(step["Step number"]), "F1", 10),
        text(x1 + 10, currentY + 7, action, "F1", 10),
        text(x2 + 10, currentY + 7, equipment, "F1", 10),
        text(x3 + 10, currentY + 7, iso, "F1", 10),
      );

        currentY -= rowHeight;
    });

    commands.push(line(innerX, bottomY, innerX + innerW, bottomY));
    commands.push(
      ...drawBottomStamp(
        "RL",
        "Route sheet",
        `${routeSheet.Steps.length} steps`,
        `Sheet ${pageIndex + 2}`,
        frame
      )
    );

    pages.push(commands.join("\n"));
  });

  return pages;
}

export function createRouteSheetPdfBlob(routeSheet: RouteSheet) {
  const pageStreams = [buildCoverPage(routeSheet), ...buildStepsPages(routeSheet)];
  const objects: string[] = [];

  const fontRegularId = 1;
  const fontBoldId = 2;
  const pagesRootId = 3;
  const firstPageObjectId = 4;

  objects[fontRegularId] = `${fontRegularId} 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj`;

  objects[fontBoldId] = `${fontBoldId} 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>
endobj`;

  const pageObjectIds: number[] = [];

  pageStreams.forEach((stream, pageIndex) => {
    const pageObjectId = firstPageObjectId + pageIndex * 2;
    const contentObjectId = pageObjectId + 1;
    pageObjectIds.push(pageObjectId);

    objects[pageObjectId] = `${pageObjectId} 0 obj
<< /Type /Page /Parent ${pagesRootId} 0 R /MediaBox [0 0 ${PAGE_WIDTH} ${PAGE_HEIGHT}] /Resources << /Font << /F1 ${fontRegularId} 0 R /F2 ${fontBoldId} 0 R >> >> /Contents ${contentObjectId} 0 R >>
endobj`;

    objects[contentObjectId] = `${contentObjectId} 0 obj
<< /Length ${stream.length} >>
stream
${stream}
endstream
endobj`;
  });

  const catalogId = firstPageObjectId + pageStreams.length * 2;

  objects[pagesRootId] = `${pagesRootId} 0 obj
<< /Type /Pages /Count ${pageObjectIds.length} /Kids [${pageObjectIds.map((id) => `${id} 0 R`).join(" ")}] >>
endobj`;

  objects[catalogId] = `${catalogId} 0 obj
<< /Type /Catalog /Pages ${pagesRootId} 0 R >>
endobj`;

  let pdf = "%PDF-1.4\n";
  const offsets: number[] = [0];

  for (let index = 1; index < objects.length; index += 1) {
    if (!objects[index]) {
      continue;
    }
    offsets[index] = pdf.length;
    pdf += `${objects[index]}\n`;
  }

  const xrefOffset = pdf.length;
  pdf += `xref
0 ${objects.length}
0000000000 65535 f 
`;

  for (let index = 1; index < objects.length; index += 1) {
    const offset = offsets[index] || 0;
    pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  }

  pdf += `trailer
<< /Size ${objects.length} /Root ${catalogId} 0 R >>
startxref
${xrefOffset}
%%EOF`;

  return new Blob([pdf], { type: "application/pdf" });
}
