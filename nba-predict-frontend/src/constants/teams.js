// 球队名称（中/英）→ NBA 标准缩写，与 init.sql 的 team 表一致
// 用于 API 只返回队名时解析缩写，进而加载队标
export const TEAM_ABBR_MAP = {
  '老鹰': 'ATL', 'Hawks': 'ATL',
  '凯尔特人': 'BOS', 'Celtics': 'BOS',
  '篮网': 'BKN', 'Nets': 'BKN',
  '黄蜂': 'CHA', 'Hornets': 'CHA',
  '公牛': 'CHI', 'Bulls': 'CHI',
  '骑士': 'CLE', 'Cavaliers': 'CLE',
  '活塞': 'DET', 'Pistons': 'DET',
  '步行者': 'IND', 'Pacers': 'IND',
  '热火': 'MIA', 'Heat': 'MIA',
  '雄鹿': 'MIL', 'Bucks': 'MIL',
  '尼克斯': 'NYK', 'Knicks': 'NYK',
  '魔术': 'ORL', 'Magic': 'ORL',
  '76人': 'PHI', '76ers': 'PHI',
  '猛龙': 'TOR', 'Raptors': 'TOR',
  '奇才': 'WAS', 'Wizards': 'WAS',
  '独行侠': 'DAL', 'Mavericks': 'DAL',
  '掘金': 'DEN', 'Nuggets': 'DEN',
  '勇士': 'GSW', 'Warriors': 'GSW',
  '火箭': 'HOU', 'Rockets': 'HOU',
  '快船': 'LAC', 'Clippers': 'LAC',
  '湖人': 'LAL', 'Lakers': 'LAL',
  '灰熊': 'MEM', 'Grizzlies': 'MEM',
  '森林狼': 'MIN', 'Timberwolves': 'MIN',
  '鹈鹕': 'NOP', 'Pelicans': 'NOP',
  '雷霆': 'OKC', 'Thunder': 'OKC',
  '太阳': 'PHX', 'Suns': 'PHX',
  '开拓者': 'POR', 'Trail Blazers': 'POR',
  '国王': 'SAC', 'Kings': 'SAC',
  '马刺': 'SAS', 'Spurs': 'SAS',
  '爵士': 'UTA', 'Jazz': 'UTA',
}

/**
 * 根据球队中英文名解析缩写，未知返回空串（TeamLogo 会显示兜底徽章）
 * @param {string} name
 * @returns {string}
 */
export const teamAbbrOf = (name) => TEAM_ABBR_MAP[name] || ''

// 球队官方主/辅色（用于对阵页背景光晕、队标辉光等视觉渲染）
export const TEAM_COLORS = {
  ATL: { primary: '#E03A3E', secondary: '#C1D32F' },
  BOS: { primary: '#007A33', secondary: '#BA9653' },
  BKN: { primary: '#333333', secondary: '#FFFFFF' },
  CHA: { primary: '#1D1160', secondary: '#00788C' },
  CHI: { primary: '#CE1141', secondary: '#000000' },
  CLE: { primary: '#860038', secondary: '#FDBC30' },
  DET: { primary: '#C8102E', secondary: '#1D42BA' },
  IND: { primary: '#002D62', secondary: '#FDBB30' },
  MIA: { primary: '#98002E', secondary: '#F9A01B' },
  MIL: { primary: '#00471B', secondary: '#EEE1C6' },
  NYK: { primary: '#006BB6', secondary: '#F58426' },
  ORL: { primary: '#0077C0', secondary: '#C4CED4' },
  PHI: { primary: '#006BB6', secondary: '#ED174C' },
  TOR: { primary: '#CE1141', secondary: '#000000' },
  WAS: { primary: '#002B5C', secondary: '#E31837' },
  DAL: { primary: '#00538C', secondary: '#B8C4CA' },
  DEN: { primary: '#0E2240', secondary: '#FEC524' },
  GSW: { primary: '#1D428A', secondary: '#FFC72C' },
  HOU: { primary: '#CE1141', secondary: '#000000' },
  LAC: { primary: '#C8102E', secondary: '#1D428A' },
  LAL: { primary: '#552583', secondary: '#FDB927' },
  MEM: { primary: '#5D76A9', secondary: '#12173F' },
  MIN: { primary: '#0C2340', secondary: '#78BE20' },
  NOP: { primary: '#0C2340', secondary: '#C8102E' },
  OKC: { primary: '#007AC1', secondary: '#EF3B24' },
  PHX: { primary: '#1D1160', secondary: '#E56020' },
  POR: { primary: '#E03A3E', secondary: '#000000' },
  SAC: { primary: '#5A2D81', secondary: '#63727A' },
  SAS: { primary: '#C4CED4', secondary: '#000000' },
  UTA: { primary: '#002B5C', secondary: '#00471B' },
}

/**
 * 根据缩写取球队主色，未知返回默认灰
 * @param {string} abbr
 * @returns {string}
 */
export const teamPrimaryColor = (abbr) => TEAM_COLORS[abbr]?.primary || '#555555'
