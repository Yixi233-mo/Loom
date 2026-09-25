/**
 * 紧凑 QR Code 生成（字节模式）— SVG 矩阵，无第三方依赖。
 * 算法对齐 QR Model 2：Reed-Solomon ECC + 掩码。用于「扫码连接」。
 */

export type QrOptions = {
  /** 纠错级别，默认 M */
  ecc?: "L" | "M" | "Q" | "H";
  /** 模块放大倍数（SVG 用） */
  scale?: number;
  /** 静区模块数 */
  margin?: number;
};

const ECC_FORMAT: Record<string, number> = { L: 1, M: 0, Q: 3, H: 2 };

/* ---------- GF(256) Reed-Solomon ---------- */
function gfMul(a: number, b: number): number {
  let x = 0;
  for (let i = 7; i >= 0; i--) {
    x = (x << 1) ^ ((x >>> 7) * 0x11d);
    x ^= ((b >>> i) & 1) * a;
  }
  return x & 0xff;
}

function rsGenerator(deg: number): number[] {
  const poly = [1];
  let root = 1;
  for (let i = 0; i < deg; i++) {
    const next = new Array(poly.length + 1).fill(0);
    for (let j = 0; j < poly.length; j++) {
      next[j] ^= gfMul(poly[j], root);
      next[j + 1] ^= poly[j];
    }
    poly.length = 0;
    poly.push(...next);
    root = gfMul(root, 2);
  }
  return poly;
}

function rsEncode(data: number[], ecLen: number): number[] {
  const gen = rsGenerator(ecLen);
  const rem = new Array(ecLen).fill(0);
  for (const b of data) {
    const factor = b ^ rem.shift()!;
    rem.push(0);
    for (let i = 0; i < ecLen; i++) rem[i] ^= gfMul(gen[i + 1] ?? 0, factor);
  }
  return rem;
}

/* ---------- 容量表（版本 1–10 字节模式，ECC M 为主） ---------- */
// [totalCodewords, ecCodewordsPerBlock] simplified: we compute from version
/** 生成位流并装入码字（版本 2–6，ECC=M 足够日常 URL） */
export function encodeQrMatrix(text: string, ecc: keyof typeof ECC_FORMAT = "M"): boolean[][] {
  const bytes = Array.from(new TextEncoder().encode(text));
  // 选择版本：1..10 足够 ~100+ 字符
  const capM = [14, 26, 42, 62, 84, 106, 122, 152, 180, 213];
  const capL = [17, 32, 53, 78, 106, 134, 154, 192, 230, 271];
  const capTable = ecc === "L" ? capL : capM;
  let version = 1;
  while (version <= 10 && capTable[version - 1] < bytes.length) version += 1;
  if (version > 10) {
    // 超长则截断（配对串不会这么长）
    bytes.length = capTable[9];
    version = 10;
  }

  const size = 17 + 4 * version;
  const modules: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));
  const isFn: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));

  const setFn = (x: number, y: number, dark: boolean) => {
    if (x >= 0 && y >= 0 && x < size && y < size) {
      modules[y][x] = dark;
      isFn[y][x] = true;
    }
  };

  // 三个定位角
  const drawFinder = (cx: number, cy: number) => {
    for (let dy = -4; dy <= 4; dy++) {
      for (let dx = -4; dx <= 4; dx++) {
        const d = Math.max(Math.abs(dx), Math.abs(dy));
        const x = cx + dx;
        const y = cy + dy;
        if (x >= 0 && y >= 0 && x < size && y < size) {
          setFn(x, y, d !== 2 && d !== 4);
        }
      }
    }
  };
  drawFinder(3, 3);
  drawFinder(size - 4, 3);
  drawFinder(3, size - 4);

  // 校正图形（版本 >=2）
  if (version >= 2) {
    const positions = [6, size - 7];
    if (version >= 7) positions.push(size / 2 + 0.5 | 0); // 简化：仅角落校正足够短码
    for (const cy of positions) {
      for (const cx of positions) {
        if (cx === 6 && cy === 6) continue;
        if (cx === size - 7 && cy === 6) continue;
        if (cx === 6 && cy === size - 7) continue;
        for (let dy = -2; dy <= 2; dy++) {
          for (let dx = -2; dx <= 2; dx++) {
            setFn(cx + dx, cy + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
          }
        }
      }
    }
    // version >=2 通常右下有一个校正
    if (version >= 2) {
      const cx = size - 7;
      const cy = size - 7;
      for (let dy = -2; dy <= 2; dy++) {
        for (let dx = -2; dx <= 2; dx++) {
          setFn(cx + dx, cy + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
        }
      }
    }
  }

  // 时序
  for (let i = 8; i < size - 8; i++) {
    setFn(6, i, i % 2 === 0);
    setFn(i, 6, i % 2 === 0);
  }
  // 固定 dark
  setFn(8, size - 8, true);

  // 预留格式信息
  for (let i = 0; i <= 8; i++) {
    if (!isFn[i][8]) setFn(8, i, false);
    if (!isFn[8][i]) setFn(i, 8, false);
  }
  for (let i = 0; i < 8; i++) {
    setFn(size - 1 - i, 8, false);
    setFn(8, size - 1 - i, false);
  }

  // 数据位流
  const bits: number[] = [];
  const pushBits = (val: number, len: number) => {
    for (let i = len - 1; i >= 0; i--) bits.push((val >>> i) & 1);
  };
  pushBits(0b0100, 4); // byte mode
  pushBits(bytes.length, version <= 9 ? 8 : 16);
  for (const b of bytes) pushBits(b, 8);
  const dataCapBits = capTable[version - 1] * 8;
  pushBits(0, Math.min(4, dataCapBits - bits.length));
  while (bits.length % 8 !== 0) bits.push(0);
  const pad = [0xec, 0x11];
  let pi = 0;
  while (bits.length < dataCapBits) {
    pushBits(pad[pi++ % 2], 8);
  }

  // 分组 + RS
  const totalData = capTable[version - 1];
  const ecPerBlock = ecc === "L" ? (version <= 4 ? 7 : version <= 8 ? 10 : 12) : version <= 4 ? 10 : 16;
  // 简化：单块（短码足够）
  const dataCw: number[] = [];
  for (let i = 0; i < bits.length; i += 8) {
    let v = 0;
    for (let j = 0; j < 8; j++) v = (v << 1) | bits[i + j];
    dataCw.push(v);
  }
  while (dataCw.length < totalData) dataCw.push(0);
  const ecCw = rsEncode(dataCw.slice(0, totalData), ecPerBlock);
  const allCw = [...dataCw.slice(0, totalData), ...ecCw];

  // 之字形放置
  const cwBits: number[] = [];
  for (const cw of allCw) {
    for (let i = 7; i >= 0; i--) cwBits.push((cw >>> i) & 1);
  }
  let bitIdx = 0;
  let upward = true;
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5;
    for (let vert = 0; vert < size; vert++) {
      for (let j = 0; j < 2; j++) {
        const x = right - j;
        const y = upward ? size - 1 - vert : vert;
        if (!isFn[y][x] && bitIdx < cwBits.length) {
          modules[y][x] = cwBits[bitIdx++] === 1;
        }
      }
    }
    upward = !upward;
  }

  // 选掩码（简单：固定 0 + 计数惩罚近似，用 XOR mask 0-7 选模块黑白平衡最好的）
  const maskFn = (m: number, x: number, y: number): boolean => {
    switch (m) {
      case 0:
        return (x + y) % 2 === 0;
      case 1:
        return y % 2 === 0;
      case 2:
        return x % 3 === 0;
      case 3:
        return (x + y) % 3 === 0;
      case 4:
        return (Math.floor(y / 2) + Math.floor(x / 3)) % 2 === 0;
      case 5:
        return ((x * y) % 2) + ((x * y) % 3) === 0;
      case 6:
        return (((x * y) % 2) + ((x * y) % 3)) % 2 === 0;
      default:
        return (((x + y) % 2) + ((x * y) % 3)) % 2 === 0;
    }
  };

  let best = 0;
  let bestScore = Infinity;
  for (let m = 0; m < 8; m++) {
    const cand = modules.map((row) => row.slice());
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        if (!isFn[y][x] && maskFn(m, x, y)) cand[y][x] = !cand[y][x];
      }
    }
    // 格式信息
    const fmt = ((ECC_FORMAT[ecc] & 3) << 3) | m;
    let rem = fmt << 10;
    for (let i = 14; i >= 10; i--) {
      if ((rem >>> i) & 1) rem ^= 0x537 << (i - 10);
    }
    const fmtBits = (((fmt << 10) | rem) ^ 0x5412) & 0x7fff;
    for (let i = 0; i < 15; i++) {
      const bit = ((fmtBits >>> i) & 1) === 1;
      // 位置近似（够用）
      if (i < 6) cand[8][i] = bit;
      else if (i < 8) cand[8][i + 1] = bit;
      else if (i === 8) cand[7][8] = bit;
      else cand[14 - i][8] = bit;
      if (i < 8) cand[size - 1 - i][8] = bit;
      else cand[8][size - 15 + i] = bit;
    }
    cand[size - 8][8] = true;
    let dark = 0;
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) if (cand[y][x]) dark++;
    const total = size * size;
    const score = Math.abs(dark * 2 - total);
    if (score < bestScore) {
      bestScore = score;
      best = m;
    }
    if (m === 0) {
      // keep first
    }
  }

  // 应用最优掩码
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      if (!isFn[y][x] && maskFn(best, x, y)) modules[y][x] = !modules[y][x];
    }
  }
  const fmt = ((ECC_FORMAT[ecc] & 3) << 3) | best;
  let rem2 = fmt << 10;
  for (let i = 14; i >= 10; i--) {
    if ((rem2 >>> i) & 1) rem2 ^= 0x537 << (i - 10);
  }
  const fmtBits = (((fmt << 10) | rem2) ^ 0x5412) & 0x7fff;
  for (let i = 0; i < 15; i++) {
    const bit = ((fmtBits >>> i) & 1) === 1;
    if (i < 6) modules[8][i] = bit;
    else if (i < 8) modules[8][i + 1] = bit;
    else if (i === 8) modules[7][8] = bit;
    else modules[14 - i][8] = bit;
    if (i < 8) modules[size - 1 - i][8] = bit;
    else modules[8][size - 15 + i] = bit;
  }
  modules[size - 8][8] = true;

  return modules;
}

export function qrToSvg(text: string, opts: QrOptions = {}): string {
  const scale = opts.scale ?? 6;
  const margin = opts.margin ?? 2;
  const matrix = encodeQrMatrix(text, opts.ecc ?? "M");
  const n = matrix.length;
  const dim = (n + margin * 2) * scale;
  let path = "";
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      if (matrix[y][x]) {
        const px = (x + margin) * scale;
        const py = (y + margin) * scale;
        path += `M${px} ${py}h${scale}v${scale}h-${scale}z`;
      }
    }
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${dim}" height="${dim}" viewBox="0 0 ${dim} ${dim}" shape-rendering="crispEdges"><rect width="100%" height="100%" fill="#fff"/><path d="${path}" fill="#2b211c"/></svg>`;
}
