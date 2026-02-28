import argparse
import subprocess
from pathlib import Path
import shutil


def convert_pdf(pdf_path: Path, output_dir: Path, dpi: int, max_dim: int, image_format: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(str(pdf_path), dpi=dpi)
        for i, image in enumerate(images, start=1):
            width, height = image.size
            if max_dim > 0 and (width > max_dim or height > max_dim):
                scale_factor = min(max_dim / width, max_dim / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height))
            image_path = output_dir / f"page_{i}.{image_format}"
            image.save(image_path)
        return len(images)
    except ModuleNotFoundError:
        pass

    try:
        import fitz
        zoom = dpi / 72.0
        doc = fitz.open(str(pdf_path))
        for i, page in enumerate(doc, start=1):
            scale_factor = 1.0
            if max_dim > 0:
                width_px = page.rect.width * zoom
                height_px = page.rect.height * zoom
                scale_factor = min(1.0, max_dim / width_px, max_dim / height_px)
            matrix = fitz.Matrix(zoom * scale_factor, zoom * scale_factor)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image_path = output_dir / f"page_{i}.{image_format}"
            pix.save(str(image_path))
        return doc.page_count
    except ModuleNotFoundError:
        pass

    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise SystemExit("未找到 pdf2image 或 PyMuPDF 或 pdftoppm，请安装其中之一")
    prefix = output_dir / "page"
    format_flag = "-png" if image_format == "png" else "-jpeg"
    subprocess.run([pdftoppm, format_flag, "-r", str(dpi), str(pdf_path), str(prefix)], check=True)
    produced = sorted(output_dir.glob("page-*.png")) + sorted(output_dir.glob("page-*.jpg")) + sorted(output_dir.glob("page-*.jpeg"))
    if max_dim > 0:
        try:
            from PIL import Image
        except ModuleNotFoundError:
            raise SystemExit("max-dim 需要 Pillow 支持，请安装 pillow 或设置 --max-dim 0")
        for img_path in produced:
            image = Image.open(img_path)
            width, height = image.size
            if width > max_dim or height > max_dim:
                scale_factor = min(max_dim / width, max_dim / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height))
                image.save(img_path)
    for i, img_path in enumerate(produced, start=1):
        target = output_dir / f"page_{i}.{img_path.suffix.lstrip('.')}"
        img_path.rename(target)
    return len(produced)


def collect_pdfs(input_path: Path):
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        return [input_path]
    if input_path.is_dir():
        return sorted(input_path.glob("*.pdf"))
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="PDF 文件或包含 PDF 的目录")
    parser.add_argument("--output", help="输出目录，默认在输入目录下生成同名文件夹", default=None)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--max-dim", type=int, default=0)
    parser.add_argument("--format", choices=["png", "jpg", "jpeg"], default="png")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    pdfs = collect_pdfs(input_path)
    if not pdfs:
        raise SystemExit(f"未找到 PDF: {input_path}")

    for pdf_path in pdfs:
        if args.output:
            output_dir = Path(args.output).expanduser().resolve()
            if input_path.is_dir():
                output_dir = output_dir / pdf_path.stem
        else:
            base_dir = pdf_path.parent
            output_dir = base_dir / f"{pdf_path.stem}_images"

        page_count = convert_pdf(
            pdf_path=pdf_path,
            output_dir=output_dir,
            dpi=args.dpi,
            max_dim=args.max_dim,
            image_format=args.format,
        )
        print(f"{pdf_path.name}: {page_count} pages -> {output_dir}")


if __name__ == "__main__":
    main()
