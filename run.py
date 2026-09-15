import argparse
import logging
import sys
from pathlib import Path

# Garantir suporte a UTF-8 no terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler

from config.settings import load_settings
from src.database.db import Database
from src.database.repository import Repository
from src.notifiers.discord import DiscordNotifier
from src.scheduler.runner import PriceGlitchOrchestrator

# Configuração de logging: ficheiro data/monitor.log + consola
log_dir = Path(__file__).resolve().parent / "data"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "monitor.log"

file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"))

console_handler = RichHandler(rich_tracebacks=True, show_path=False)
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler],
)
logger = logging.getLogger("app")
console = Console()


def show_stats(settings):
    """Mostra um sumário formatado do estado da base de dados."""
    db = Database(settings.database_path)
    repo = Repository(db)
    stats = repo.get_stats()

    console.print("\n[bold cyan]📊 ESTATÍSTICAS DA BASE DE DADOS (SQLite)[/bold cyan]")
    console.print(f"📁 Ficheiro: [yellow]{settings.database_path}[/yellow]\n")

    summary_table = Table(title="Resumo Global", show_header=True, header_style="bold magenta")
    summary_table.add_column("Métrica", style="dim")
    summary_table.add_column("Valor", justify="right", style="bold green")

    summary_table.add_row("Total de Produtos Monitorizados", str(stats["total_products"]))
    summary_table.add_row("Total de Preços Registados", str(stats["total_prices_logged"]))
    summary_table.add_row("Total de Alertas de Falha Enviados", str(stats["total_alerts_sent"]))
    console.print(summary_table)

    if stats["categories"]:
        cat_table = Table(title="Produtos por Categoria", show_header=True, header_style="bold blue")
        cat_table.add_column("ID da Categoria")
        cat_table.add_column("Qtd Produtos", justify="right")
        for cat_id, count in stats["categories"].items():
            cat_table.add_row(cat_id, str(count))
        console.print(cat_table)


def main():
    parser = argparse.ArgumentParser(
        description="Monitor de Falhas de Preço (Price Glitches) — Amazon Gaming & Tech",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Executa uma ronda imediata de varrimento e termina.",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Inicia o agendador em loop contínuo (APScheduler).",
    )
    parser.add_argument(
        "--test-discord",
        action="store_true",
        help="Envia uma mensagem de teste para o webhook do Discord configurado.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Mostra estatísticas da base de dados.",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Filtra a execução do scan para apenas uma categoria específica (ex: 'gpu', 'cpu', 'smartphones').",
    )

    args = parser.parse_args()

    # Se nenhum argumento for passado, mostra o menu de ajuda
    if not (args.scan or args.daemon or args.test_discord or args.stats):
        parser.print_help()
        console.print("\n[yellow]💡 Exemplo de uso rápido:[/yellow]")
        console.print("  [cyan]python run.py --test-discord[/cyan]   # Testar webhook do Discord")
        console.print("  [cyan]python run.py --scan[/cyan]           # Executar uma ronda de teste agora")
        console.print("  [cyan]python run.py --daemon[/cyan]         # Iniciar monitorização contínua 24/7")
        console.print("  [cyan]python run.py --stats[/cyan]          # Ver dados acumulados")
        sys.exit(0)

    settings = load_settings()

    # 1. Teste de Discord
    if args.test_discord:
        if not settings.discord_webhook_url:
            console.print("[bold red]❌ ERRO:[/bold red] Variável DISCORD_WEBHOOK_URL não encontrada no ficheiro .env!")
            console.print("Crie um ficheiro .env na raiz do projeto com:")
            console.print("DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
            sys.exit(1)
        console.print(f"[cyan]A enviar mensagem de teste para o Discord...[/cyan]")
        notifier = DiscordNotifier(settings.discord_webhook_url)
        success = notifier.send_test_message()
        if success:
            console.print("[bold green]✅ Sucesso![/bold green] Verifique o seu canal do Discord.")
        else:
            console.print("[bold red]❌ Falha ao enviar mensagem.[/bold red] Verifique a URL do webhook.")
        return

    # 2. Estatísticas
    if args.stats:
        show_stats(settings)
        return

    # Se filtrou por categoria específica
    if args.category:
        filtered = [c for c in settings.categories if c.id.lower() == args.category.lower()]
        if not filtered:
            console.print(f"[bold red]❌ Categoria '{args.category}' não encontrada no config.yaml![/bold red]")
            console.print(f"Categorias disponíveis: {', '.join(c.id for c in settings.categories)}")
            sys.exit(1)
        settings.categories = filtered
        console.print(f"[cyan]Foco restrito à categoria:[/cyan] [bold]{filtered[0].name}[/bold]")

    orchestrator = PriceGlitchOrchestrator(settings)

    # 3. Scan imediato único
    if args.scan:
        console.print("[bold green]Iniciando scan único imediato...[/bold green]")
        orchestrator.run_cycle()
        show_stats(settings)

    # 4. Agendador contínuo
    elif args.daemon:
        console.print("[bold green]Iniciando monitor de falhas de preço em modo contínuo (daemon)...[/bold green]")
        orchestrator.start_scheduler()


if __name__ == "__main__":
    main()
