import { cpSync, mkdirSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const projectRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const outputDirectory = join(projectRoot, "www");
const files = [
  "teste.html",
  "game.py",
  "fazenda_logica.py",
  "insumos.json",
  "style.css"
];

rmSync(outputDirectory, { recursive: true, force: true });
mkdirSync(outputDirectory, { recursive: true });

for (const file of files) {
  const destination = file === "teste.html" ? "index.html" : file;
  cpSync(join(projectRoot, file), join(outputDirectory, destination));
}

cpSync(join(projectRoot, "offline"), join(outputDirectory, "offline"), {
  recursive: true,
  filter: (source) => !source.endsWith(".map")
});

console.log(`Android web assets prepared in ${outputDirectory}`);
