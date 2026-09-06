import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";

function createPng(width, height) {
  // Simple uncompressed/deflated raw RGBA bitmap
  const rowSize = width * 4 + 1;
  const rawData = Buffer.alloc(rowSize * height);

  for (let y = 0; y < height; y++) {
    const rowOffset = y * rowSize;
    rawData[rowOffset] = 0; // Filter byte: None

    for (let x = 0; x < width; x++) {
      const pixelOffset = rowOffset + 1 + x * 4;

      // Draw YouTube Red (#FF0000) rounded background
      const r = width / 2;
      const dx = x - r;
      const dy = y - r;
      const dist = Math.sqrt(dx * dx + dy * dy);

      // Play triangle in white
      const isInPlayTriangle =
        x >= width * 0.38 &&
        x <= width * 0.68 &&
        y >= height * 0.3 &&
        y <= height * 0.7 &&
        y - height * 0.5 <= (x - width * 0.38) * 0.7 &&
        height * 0.5 - y <= (x - width * 0.38) * 0.7;

      if (isInPlayTriangle) {
        rawData[pixelOffset] = 255; // R
        rawData[pixelOffset + 1] = 255; // G
        rawData[pixelOffset + 2] = 255; // B
        rawData[pixelOffset + 3] = 255; // A
      } else if (dist <= r) {
        rawData[pixelOffset] = 239; // R (Tailwind Red 600)
        rawData[pixelOffset + 1] = 68; // G
        rawData[pixelOffset + 2] = 68; // B
        rawData[pixelOffset + 3] = 255; // A
      } else {
        rawData[pixelOffset] = 0;
        rawData[pixelOffset + 1] = 0;
        rawData[pixelOffset + 2] = 0;
        rawData[pixelOffset + 3] = 0; // Transparent
      }
    }
  }

  const deflated = zlib.deflateSync(rawData);

  function crc32(buf) {
    let c = 0xffffffff;
    for (let i = 0; i < buf.length; i++) {
      c ^= buf[i];
      for (let k = 0; k < 8; k++) {
        c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      }
    }
    return (c ^ 0xffffffff) >>> 0;
  }

  function chunk(type, data) {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length, 0);
    const typeBuf = Buffer.from(type, "ascii");
    const crcBuf = Buffer.alloc(4);
    crcBuf.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])), 0);
    return Buffer.concat([len, typeBuf, data, crcBuf]);
  }

  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8; // 8-bit depth
  ihdrData[9] = 6; // RGBA
  ihdrData[10] = 0; // Compression
  ihdrData[11] = 0; // Filter
  ihdrData[12] = 0; // Interlace

  const ihdr = chunk("IHDR", ihdrData);
  const idat = chunk("IDAT", deflated);
  const iend = chunk("IEND", Buffer.alloc(0));

  return Buffer.concat([signature, ihdr, idat, iend]);
}

const outDir = path.resolve("public/icon");
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

for (const size of [16, 32, 48, 128]) {
  const png = createPng(size, size);
  fs.writeFileSync(path.join(outDir, `${size}.png`), png);
  console.log(`Generated public/icon/${size}.png`);
}
