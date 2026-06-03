/**
 * Design System Showcase
 *
 * A single-page visual reference of every design token and UI component
 * in the project. Each section shows the source file path for quick editing.
 *
 * Route: /design-system
 * This page is self-contained and does not affect other routes.
 */

import { Button, Card, Badge, Score, MetricBar } from '../components/ui';

/* ---------------------------------------------------------------------------
 * Token data — hardcoded from tokens.css for static display.
 * Grouped to match the comment structure in the source file.
 * ----------------------------------------------------------------------- */

const BASE_PATH = 'frontend/src';

interface ColorToken {
  name: string;
  value: string;
}

interface ColorGroup {
  title: string;
  tokens: ColorToken[];
}

const COLOR_GROUPS: ColorGroup[] = [
  {
    title: 'Core',
    tokens: [
      { name: '--color-primary', value: '#059669' },
      { name: '--color-primary-hover', value: '#047857' },
      { name: '--color-primary-soft', value: '#ECFDF5' },
    ],
  },
  {
    title: 'Secondary',
    tokens: [
      { name: '--color-secondary', value: '#4C4C4C' },
      { name: '--color-secondary-dark', value: '#003c33' },
    ],
  },
  {
    title: 'Surface',
    tokens: [
      { name: '--color-bg', value: '#ffffff' },
      { name: '--color-surface', value: '#ffffff' },
      { name: '--color-surface-alt', value: '#F4F4F5' },
    ],
  },
  {
    title: 'Text',
    tokens: [
      { name: '--color-text', value: '#212121' },
      { name: '--color-text-muted', value: '#75758a' },
      { name: '--color-text-subtle', value: '#93939f' },
    ],
  },
  {
    title: 'Border',
    tokens: [
      { name: '--color-border', value: '#e5e7eb' },
      { name: '--color-divider', value: '#d9d9dd' },
    ],
  },
  {
    title: 'Accent',
    tokens: [
      { name: '--color-accent', value: '#ff7759' },
      { name: '--color-link', value: '#1863dc' },
    ],
  },
  {
    title: 'Status / MetricBar',
    tokens: [
      { name: '--color-danger', value: '#FB6666' },
      { name: '--color-danger-soft', value: '#FEE2E2' },
      { name: '--color-warning', value: '#FFD82A' },
      { name: '--color-warning-soft', value: '#FFF8E1' },
      { name: '--color-success', value: '#059669' },
      { name: '--color-success-soft', value: '#ECFDF5' },
      { name: '--color-info', value: '#5570F1' },
      { name: '--color-info-soft', value: '#C1CCFF' },
    ],
  },
  {
    title: 'Focus',
    tokens: [
      { name: '--color-focus-ring', value: 'rgba(5,150,105,0.40)' },
    ],
  },
  {
    title: 'Heatmap',
    tokens: [
      { name: '--heatmap-1', value: '#edfce9' },
      { name: '--heatmap-2', value: '#b9dfb6' },
      { name: '--heatmap-3', value: '#6fa985' },
      { name: '--heatmap-4', value: '#2c7559' },
      { name: '--heatmap-5', value: '#003c33' },
    ],
  },
  {
    title: 'Subway Lines',
    tokens: [
      { name: '--subway-line-1', value: '#0052A4' },
      { name: '--subway-line-2', value: '#00A84D' },
      { name: '--subway-line-3', value: '#EF7C1C' },
      { name: '--subway-line-4', value: '#00A5DE' },
      { name: '--subway-line-5', value: '#996CAC' },
      { name: '--subway-line-6', value: '#CD7C2F' },
      { name: '--subway-line-7', value: '#747F00' },
      { name: '--subway-line-8', value: '#E6186C' },
      { name: '--subway-line-9', value: '#BDB092' },
    ],
  },
];

interface TypographyToken {
  name: string;
  size: string;
  line: string;
  weight: string;
  tracking: string;
  sample: string;
}

const TYPOGRAPHY_TOKENS: TypographyToken[] = [
  {
    name: 'Hero Display',
    size: '80px',
    line: '1.00',
    weight: '700',
    tracking: '-1.6px',
    sample: '슬기로운 자취생활',
  },
  {
    name: 'Page Display',
    size: '60px',
    line: '1.00',
    weight: '700',
    tracking: '-1.2px',
    sample: '동네 브리핑',
  },
  {
    name: 'Section Display',
    size: '48px',
    line: '1.05',
    weight: '600',
    tracking: '-0.96px',
    sample: '평균 전월세',
  },
  {
    name: 'Section Heading',
    size: '36px',
    line: '1.15',
    weight: '600',
    tracking: '-0.36px',
    sample: '비교 분석',
  },
  {
    name: 'Card Heading',
    size: '28px',
    line: '1.20',
    weight: '600',
    tracking: '-0.28px',
    sample: '종합 점수 카드',
  },
  {
    name: 'Feature Heading',
    size: '22px',
    line: '1.30',
    weight: '600',
    tracking: '0',
    sample: 'POI 카테고리 헤더',
  },
  {
    name: 'Body Large',
    size: '18px',
    line: '1.50',
    weight: '400',
    tracking: '0',
    sample: '리드 단락, 브리핑 요약 텍스트입니다. 이 크기는 중요 본문에 사용합니다.',
  },
  {
    name: 'Body Base',
    size: '16px',
    line: '1.60',
    weight: '400',
    tracking: '0',
    sample: '기본 본문 텍스트입니다. 표 셀, 일반 설명 등 가장 많이 사용하는 크기.',
  },
  {
    name: 'Button',
    size: '14px',
    line: '1.40',
    weight: '600',
    tracking: '0',
    sample: '탐색 시작하기',
  },
  {
    name: 'Caption Base',
    size: '14px',
    line: '1.40',
    weight: '400',
    tracking: '0',
    sample: '메타, 거래 5건, 날짜',
  },
  {
    name: 'Mono Label',
    size: '13px',
    line: '1.40',
    weight: '400',
    tracking: '0.26px',
    sample: 'WALK 5MIN  |  LINE 3  |  PERCENTILE 87',
  },
  {
    name: 'Micro',
    size: '12px',
    line: '1.40',
    weight: '400',
    tracking: '0',
    sample: 'footer, nav micro copy, 최소 텍스트',
  },
  {
    name: 'Data Display',
    size: '48px',
    line: '1.00',
    weight: '600',
    tracking: '-0.48px',
    sample: '55만원',
  },
];

interface SpaceToken {
  name: string;
  value: string;
}

const SPACING_TOKENS: SpaceToken[] = [
  { name: '--space-1', value: '4px' },
  { name: '--space-2', value: '8px' },
  { name: '--space-3', value: '12px' },
  { name: '--space-4', value: '16px' },
  { name: '--space-5', value: '20px' },
  { name: '--space-6', value: '24px' },
  { name: '--space-8', value: '32px' },
  { name: '--space-10', value: '40px' },
  { name: '--space-14', value: '56px' },
  { name: '--space-16', value: '64px' },
  { name: '--space-20', value: '80px' },
  { name: '--space-30', value: '120px' },
];

interface RadiusToken {
  name: string;
  value: string;
  description: string;
}

const RADIUS_TOKENS: RadiusToken[] = [
  { name: '--radius-xs', value: '4px', description: 'legend, table cell' },
  { name: '--radius-sm', value: '8px', description: 'button, input — control surface' },
  { name: '--radius-md', value: '8px', description: 'alias of sm; CTA / modal / panel' },
  { name: '--radius-card', value: '16px', description: 'data block, summary card' },
  { name: '--radius-hero', value: '22px', description: 'hero photo, large media' },
  { name: '--radius-xl', value: '30px', description: 'filter pill outline' },
  { name: '--radius-pill', value: '32px', description: 'large filter chip (filled)' },
  { name: '--radius-full', value: '9999px', description: 'round status dots' },
];

interface HeightToken {
  name: string;
  value: string;
}

const HEIGHT_TOKENS: HeightToken[] = [
  { name: '--control-height-sm', value: '32px' },
  { name: '--control-height-md', value: '40px' },
  { name: '--control-height-cta', value: '44px' },
  { name: '--control-height-lg', value: '48px' },
  { name: '--badge-height', value: '22px' },
];

interface TransitionToken {
  name: string;
  value: string;
}

const TRANSITION_TOKENS: TransitionToken[] = [
  { name: '--transition-fast', value: '120ms ease-out' },
  { name: '--transition-base', value: '200ms ease-out' },
  { name: '--transition-slow', value: '300ms ease-out' },
];

interface ZIndexToken {
  name: string;
  value: string;
}

const ZINDEX_TOKENS: ZIndexToken[] = [
  { name: '--z-modal-backdrop', value: '1000' },
  { name: '--z-modal', value: '1010' },
  { name: '--z-tooltip', value: '1100' },
];

/* ---------------------------------------------------------------------------
 * Style constants for the showcase layout (inline styles, self-contained)
 * ----------------------------------------------------------------------- */

const styles = {
  page: {
    maxWidth: 1280,
    margin: '0 auto',
    padding: 'var(--space-10) var(--space-6)',
    fontFamily: 'var(--font-family-base)',
    color: 'var(--color-text)',
    background: 'var(--color-bg)',
  } as const,
  pageTitle: {
    fontSize: 'var(--font-page-display-size)',
    lineHeight: 'var(--font-page-display-line)',
    letterSpacing: 'var(--font-page-display-tracking)',
    fontWeight: 400,
    marginBottom: 'var(--space-2)',
  } as const,
  pageSubtitle: {
    fontSize: 'var(--font-body-large-size)',
    lineHeight: 'var(--font-body-large-line)',
    color: 'var(--color-text-muted)',
    marginBottom: 'var(--space-16)',
  } as const,
  section: {
    marginBottom: 'var(--space-20)',
  } as const,
  sectionHeading: {
    fontSize: 'var(--font-section-heading-size)',
    lineHeight: 'var(--font-section-heading-line)',
    letterSpacing: 'var(--font-section-heading-tracking)',
    fontWeight: 400,
    marginBottom: 'var(--space-2)',
    paddingBottom: 'var(--space-3)',
    borderBottom: '1px solid var(--color-divider)',
  } as const,
  editPath: {
    fontSize: 'var(--font-micro-size)',
    color: 'var(--color-text-subtle)',
    marginBottom: 'var(--space-6)',
    display: 'block',
    fontFamily: 'var(--font-family-mono)',
  } as const,
  subHeading: {
    fontSize: 'var(--font-feature-heading-size)',
    lineHeight: 'var(--font-feature-heading-line)',
    fontWeight: 400,
    marginBottom: 'var(--space-4)',
    marginTop: 'var(--space-6)',
  } as const,
  swatchGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
    gap: 'var(--space-4)',
    marginBottom: 'var(--space-6)',
  } as const,
  swatchBox: {
    borderRadius: 'var(--radius-sm)',
    overflow: 'hidden',
    border: '1px solid var(--color-border)',
  } as const,
  swatchColor: {
    height: 64,
    width: '100%',
  } as const,
  swatchInfo: {
    padding: 'var(--space-2) var(--space-3)',
    fontSize: 'var(--font-micro-size)',
    lineHeight: 1.4,
  } as const,
  swatchName: {
    display: 'block',
    fontFamily: 'var(--font-family-mono)',
    color: 'var(--color-text)',
    wordBreak: 'break-all' as const,
    marginBottom: 2,
  } as const,
  swatchHex: {
    display: 'block',
    color: 'var(--color-text-muted)',
    fontFamily: 'var(--font-family-mono)',
    textTransform: 'uppercase' as const,
  } as const,
  typeRow: {
    marginBottom: 'var(--space-6)',
    paddingBottom: 'var(--space-4)',
    borderBottom: '1px solid var(--color-border)',
  } as const,
  typeMeta: {
    fontSize: 'var(--font-micro-size)',
    fontFamily: 'var(--font-family-mono)',
    color: 'var(--color-text-muted)',
    marginBottom: 'var(--space-2)',
    display: 'flex',
    gap: 'var(--space-4)',
    flexWrap: 'wrap' as const,
  } as const,
  spacingRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-4)',
    marginBottom: 'var(--space-3)',
  } as const,
  spacingLabel: {
    width: 120,
    fontSize: 'var(--font-micro-size)',
    fontFamily: 'var(--font-family-mono)',
    color: 'var(--color-text)',
    flexShrink: 0,
  } as const,
  spacingValue: {
    width: 48,
    fontSize: 'var(--font-micro-size)',
    fontFamily: 'var(--font-family-mono)',
    color: 'var(--color-text-muted)',
    flexShrink: 0,
    textAlign: 'right' as const,
  } as const,
  spacingBar: {
    height: 16,
    background: 'var(--color-secondary-dark)',
    borderRadius: 'var(--radius-xs)',
    opacity: 0.7,
  } as const,
  radiusGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
    gap: 'var(--space-4)',
  } as const,
  radiusBox: {
    width: '100%',
    height: 100,
    background: 'var(--color-surface-alt)',
    border: '2px solid var(--color-divider)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'column' as const,
    gap: 4,
  } as const,
  radiusName: {
    fontSize: 'var(--font-micro-size)',
    fontFamily: 'var(--font-family-mono)',
    color: 'var(--color-text)',
  } as const,
  radiusVal: {
    fontSize: 'var(--font-micro-size)',
    fontFamily: 'var(--font-family-mono)',
    color: 'var(--color-text-muted)',
  } as const,
  shadowBox: {
    width: 200,
    height: 120,
    background: 'var(--color-surface)',
    borderRadius: 'var(--radius-card)',
    boxShadow: 'var(--shadow-floating)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 'var(--font-micro-size)',
    fontFamily: 'var(--font-family-mono)',
    color: 'var(--color-text-muted)',
  } as const,
  heightRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-4)',
    marginBottom: 'var(--space-3)',
  } as const,
  heightLabel: {
    width: 180,
    fontSize: 'var(--font-micro-size)',
    fontFamily: 'var(--font-family-mono)',
    color: 'var(--color-text)',
    flexShrink: 0,
  } as const,
  heightBar: {
    background: 'var(--color-secondary)',
    borderRadius: 'var(--radius-xs)',
    width: 200,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--color-surface)',
    fontSize: 'var(--font-micro-size)',
    fontFamily: 'var(--font-family-mono)',
  } as const,
  tokenList: {
    display: 'grid',
    gridTemplateColumns: '240px 1fr',
    gap: 'var(--space-2) var(--space-6)',
    fontSize: 'var(--font-caption-base-size)',
    fontFamily: 'var(--font-family-mono)',
  } as const,
  tokenName: {
    color: 'var(--color-text)',
  } as const,
  tokenValue: {
    color: 'var(--color-text-muted)',
  } as const,
  componentRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: 'var(--space-4)',
    alignItems: 'center',
    marginBottom: 'var(--space-4)',
  } as const,
  componentLabel: {
    fontSize: 'var(--font-caption-base-size)',
    color: 'var(--color-text-muted)',
    marginBottom: 'var(--space-2)',
    fontFamily: 'var(--font-family-mono)',
  } as const,
  componentGroup: {
    marginBottom: 'var(--space-6)',
  } as const,
  metricBarWrap: {
    maxWidth: 360,
    marginBottom: 'var(--space-3)',
  } as const,
} as const;

/* ---------------------------------------------------------------------------
 * Component
 * ----------------------------------------------------------------------- */

function SectionTitle({
  title,
  editFile,
}: {
  title: string;
  editFile: string;
}) {
  return (
    <>
      <h2 style={styles.sectionHeading}>{title}</h2>
      <span style={styles.editPath}>
        수정 파일: {editFile}
      </span>
    </>
  );
}

function ColorSwatches() {
  return (
    <section style={styles.section}>
      <SectionTitle
        title="Colors"
        editFile={`${BASE_PATH}/styles/globals.css`}
      />
      {COLOR_GROUPS.map((group) => (
        <div key={group.title}>
          <h3 style={styles.subHeading}>{group.title}</h3>
          <div style={styles.swatchGrid}>
            {group.tokens.map((token) => (
              <div key={token.name} style={styles.swatchBox}>
                <div
                  style={{
                    ...styles.swatchColor,
                    backgroundColor: token.value,
                  }}
                />
                <div style={styles.swatchInfo}>
                  <span style={styles.swatchName}>{token.name}</span>
                  <span style={styles.swatchHex}>{token.value}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

function TypographyShowcase() {
  return (
    <section style={styles.section}>
      <SectionTitle
        title="Typography"
        editFile={`${BASE_PATH}/styles/globals.css`}
      />
      {TYPOGRAPHY_TOKENS.map((token) => {
        const isMonoLabel = token.name === 'Mono Label';
        return (
          <div key={token.name} style={styles.typeRow}>
            <div style={styles.typeMeta}>
              <span>{token.name}</span>
              <span>size: {token.size}</span>
              <span>line: {token.line}</span>
              <span>weight: {token.weight}</span>
              <span>tracking: {token.tracking}</span>
            </div>
            <div
              style={{
                fontSize: token.size,
                lineHeight: token.line,
                fontWeight: Number(token.weight),
                letterSpacing: token.tracking,
                fontFamily: isMonoLabel
                  ? 'var(--font-family-mono)'
                  : 'var(--font-family-base)',
                color: 'var(--color-text)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {token.sample}
            </div>
          </div>
        );
      })}
    </section>
  );
}

function SpacingShowcase() {
  return (
    <section style={styles.section}>
      <SectionTitle
        title="Spacing"
        editFile={`${BASE_PATH}/styles/globals.css`}
      />
      {SPACING_TOKENS.map((token) => (
        <div key={token.name} style={styles.spacingRow}>
          <span style={styles.spacingLabel}>{token.name}</span>
          <span style={styles.spacingValue}>{token.value}</span>
          <div
            style={{
              ...styles.spacingBar,
              width: token.value,
            }}
          />
        </div>
      ))}
    </section>
  );
}

function RadiusShowcase() {
  return (
    <section style={styles.section}>
      <SectionTitle
        title="Radius"
        editFile={`${BASE_PATH}/styles/globals.css`}
      />
      <div style={styles.radiusGrid}>
        {RADIUS_TOKENS.map((token) => (
          <div
            key={token.name}
            style={{
              ...styles.radiusBox,
              borderRadius: token.value,
            }}
          >
            <span style={styles.radiusName}>{token.name}</span>
            <span style={styles.radiusVal}>{token.value}</span>
            <span
              style={{
                ...styles.radiusVal,
                fontSize: 11,
                maxWidth: '80%',
                textAlign: 'center',
              }}
            >
              {token.description}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ShadowShowcase() {
  return (
    <section style={styles.section}>
      <SectionTitle
        title="Shadows"
        editFile={`${BASE_PATH}/styles/globals.css`}
      />
      <div style={styles.shadowBox}>--shadow-floating</div>
    </section>
  );
}

function HeightShowcase() {
  return (
    <section style={styles.section}>
      <SectionTitle
        title="Component Heights"
        editFile={`${BASE_PATH}/styles/globals.css`}
      />
      {HEIGHT_TOKENS.map((token) => (
        <div key={token.name} style={styles.heightRow}>
          <span style={styles.heightLabel}>{token.name}</span>
          <div
            style={{
              ...styles.heightBar,
              height: token.value,
            }}
          >
            {token.value}
          </div>
        </div>
      ))}
    </section>
  );
}

function TransitionShowcase() {
  return (
    <section style={styles.section}>
      <SectionTitle
        title="Transitions"
        editFile={`${BASE_PATH}/styles/globals.css`}
      />
      <div style={styles.tokenList}>
        {TRANSITION_TOKENS.map((token) => (
          <div key={token.name} style={{ display: 'contents' }}>
            <span style={styles.tokenName}>{token.name}</span>
            <span style={styles.tokenValue}>{token.value}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ZIndexShowcase() {
  return (
    <section style={styles.section}>
      <SectionTitle
        title="Z-Index"
        editFile={`${BASE_PATH}/styles/globals.css`}
      />
      <div style={styles.tokenList}>
        {ZINDEX_TOKENS.map((token) => (
          <div key={token.name} style={{ display: 'contents' }}>
            <span style={styles.tokenName}>{token.name}</span>
            <span style={styles.tokenValue}>{token.value}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ButtonShowcase() {
  const variants = ['primary', 'secondary', 'outline', 'filled', 'ghost'] as const;
  const sizes = ['sm', 'md', 'lg'] as const;

  return (
    <section style={styles.section}>
      <SectionTitle
        title="Button"
        editFile={`${BASE_PATH}/components/ui/Button.tsx`}
      />
      {variants.map((variant) => (
        <div key={variant} style={styles.componentGroup}>
          <div style={styles.componentLabel}>variant="{variant}"</div>
          <div style={styles.componentRow}>
            {sizes.map((size) => (
              <Button key={size} variant={variant} size={size}>
                {variant} / {size}
              </Button>
            ))}
            <Button variant={variant} disabled>
              disabled
            </Button>
          </div>
        </div>
      ))}
      <div style={styles.componentGroup}>
        <div style={styles.componentLabel}>loading states</div>
        <div style={styles.componentRow}>
          <Button loading>Loading primary</Button>
          <Button variant="outline" loading>
            Loading outline
          </Button>
          <Button variant="filled" loading>
            Loading filled
          </Button>
        </div>
      </div>
      <div style={styles.componentGroup}>
        <div style={styles.componentLabel}>fullWidth</div>
        <div style={{ maxWidth: 400 }}>
          <Button fullWidth>Full Width Primary</Button>
        </div>
      </div>
    </section>
  );
}

function CardShowcase() {
  return (
    <section style={styles.section}>
      <SectionTitle
        title="Card"
        editFile={`${BASE_PATH}/components/ui/Card.tsx`}
      />
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 'var(--space-6)',
          maxWidth: 700,
        }}
      >
        <div style={styles.componentGroup}>
          <div style={styles.componentLabel}>variant="default" padding="md"</div>
          <Card>
            <div style={{ fontSize: 'var(--font-body-base-size)' }}>
              Default Card
            </div>
            <div
              style={{
                fontSize: 'var(--font-caption-base-size)',
                color: 'var(--color-text-muted)',
                marginTop: 'var(--space-2)',
              }}
            >
              White surface, 16px padding, 1px border.
            </div>
          </Card>
        </div>
        <div style={styles.componentGroup}>
          <div style={styles.componentLabel}>variant="inset" padding="lg"</div>
          <Card variant="inset" padding="lg">
            <div style={{ fontSize: 'var(--font-body-base-size)' }}>
              Inset Card
            </div>
            <div
              style={{
                fontSize: 'var(--font-caption-base-size)',
                color: 'var(--color-text-muted)',
                marginTop: 'var(--space-2)',
              }}
            >
              Soft Stone surface, 20px padding.
            </div>
          </Card>
        </div>
        <div style={styles.componentGroup}>
          <div style={styles.componentLabel}>padding="none"</div>
          <Card padding="none">
            <div
              style={{
                padding: 'var(--space-4)',
                borderBottom: '1px solid var(--color-border)',
                fontSize: 'var(--font-body-base-size)',
              }}
            >
              Header Zone
            </div>
            <div
              style={{
                padding: 'var(--space-4)',
                fontSize: 'var(--font-caption-base-size)',
                color: 'var(--color-text-muted)',
              }}
            >
              Body Zone (custom layout with padding="none")
            </div>
          </Card>
        </div>
      </div>
    </section>
  );
}

function BadgeShowcase() {
  const variants = [
    'success',
    'warning',
    'danger',
    'info',
    'neutral',
    'category',
    'mono',
  ] as const;
  const sizes = ['sm', 'md'] as const;

  const sampleText: Record<string, string> = {
    success: '충분',
    warning: '보통',
    danger: '부족',
    info: '정보',
    neutral: '편의점 12개',
    category: '대학가형',
    mono: 'WALK 5MIN',
  };

  return (
    <section style={styles.section}>
      <SectionTitle
        title="Badge"
        editFile={`${BASE_PATH}/components/ui/Badge.tsx`}
      />
      {sizes.map((size) => (
        <div key={size} style={styles.componentGroup}>
          <div style={styles.componentLabel}>size="{size}"</div>
          <div style={styles.componentRow}>
            {variants.map((variant) => (
              <Badge key={variant} variant={variant} size={size}>
                {sampleText[variant]}
              </Badge>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

function ScoreShowcase() {
  const scores = [
    { value: 20, label: 'Low score (auto-tone: danger)' },
    { value: 55, label: 'Mid score (auto-tone: warning)' },
    { value: 85, label: 'High score (auto-tone: success)' },
  ];

  return (
    <section style={styles.section}>
      <SectionTitle
        title="Score"
        editFile={`${BASE_PATH}/components/ui/Score.tsx`}
      />
      <div style={styles.componentGroup}>
        <div style={styles.componentLabel}>size="md" (auto-tone)</div>
        <div style={styles.componentRow}>
          {scores.map((s) => (
            <div key={s.value} style={{ textAlign: 'center' }}>
              <Score value={s.value} unit="/ 100" />
              <div
                style={{
                  fontSize: 'var(--font-micro-size)',
                  color: 'var(--color-text-muted)',
                  marginTop: 'var(--space-2)',
                }}
              >
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div style={styles.componentGroup}>
        <div style={styles.componentLabel}>size="lg" with delta</div>
        <div style={styles.componentRow}>
          <Score value={78} unit="점" size="lg" delta={4} />
          <Score value={45} unit="점" size="lg" delta={-3} />
          <Score value={62} size="lg" tone="neutral" />
        </div>
      </div>
    </section>
  );
}

function MetricBarShowcase() {
  return (
    <section style={styles.section}>
      <SectionTitle
        title="MetricBar"
        editFile={`${BASE_PATH}/components/ui/MetricBar.tsx`}
      />
      <div style={styles.componentGroup}>
        <div style={styles.componentLabel}>tone="score" (status-aligned fills)</div>
        <div style={styles.metricBarWrap}>
          <MetricBar label="교통" value={15} tone="score" />
        </div>
        <div style={styles.metricBarWrap}>
          <MetricBar label="안전" value={35} tone="score" />
        </div>
        <div style={styles.metricBarWrap}>
          <MetricBar label="편의시설" value={55} tone="score" />
        </div>
        <div style={styles.metricBarWrap}>
          <MetricBar label="문화/여가" value={75} tone="score" />
        </div>
        <div style={styles.metricBarWrap}>
          <MetricBar label="전월세" value={92} tone="score" />
        </div>
      </div>
      <div style={styles.componentGroup}>
        <div style={styles.componentLabel}>tone="weight" (primary fill)</div>
        <div style={styles.metricBarWrap}>
          <MetricBar label="전월세 가중치" value={80} tone="weight" unit="%" />
        </div>
        <div style={styles.metricBarWrap}>
          <MetricBar label="교통 가중치" value={40} tone="weight" unit="%" />
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------------------
 * Main page component
 * ----------------------------------------------------------------------- */

export default function DesignSystem() {
  return (
    <main style={styles.page}>
      <h1 style={styles.pageTitle}>Design System</h1>
      <p style={styles.pageSubtitle}>
        모든 디자인 토큰과 UI 컴포넌트를 한 눈에 확인할 수 있는 쇼케이스 페이지입니다.
        각 섹션 하단에 수정 파일 경로가 표시됩니다.
      </p>

      <ColorSwatches />
      <TypographyShowcase />
      <SpacingShowcase />
      <RadiusShowcase />
      <ShadowShowcase />
      <HeightShowcase />
      <TransitionShowcase />
      <ZIndexShowcase />
      <ButtonShowcase />
      <CardShowcase />
      <BadgeShowcase />
      <ScoreShowcase />
      <MetricBarShowcase />
    </main>
  );
}
