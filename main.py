"""Build a standalone offline atlas using the existing embedded route dataset."""
import re
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    source = (root / 'swiss_routes.html').read_text()
    match = re.search(r"atob\('([^']+)'\)", source)
    if match is None:
        raise ValueError('Embedded route dataset not found')
    template = (root / 'src/map.html').read_text()
    output = root / 'beijing_route_atlas.html'
    for token, filename in [('__FRONTIER_CSS__', 'frontier.css'),
                            ('__THEME_CSS__', 'theme.css'),
                            ('__FONT_LINKS__', 'font-links.html'),
                            ('__COMPARISON_JS__', 'comparison.js'),
                            ('__MAP_RENDERER_JS__', 'map-renderer.js')]:
        template = template.replace(token, (root / 'src' / filename).read_text())
    output.write_text(template.replace('__DATA__', match.group(1)))
    print(f'Built {output.name}: {output.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
