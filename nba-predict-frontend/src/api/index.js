import request from './request'

// 球员接口
export const playerApi = {
  getList: (params) => request.get('/player/list', { params }),
  getDetail: (id, config) => request.get(`/player/detail/${id}`, config),
  predict: (data) => request.post('/player/predict', data),
  backtest: (data) => request.post('/player/backtest', data),
}

// 球队接口
export const teamApi = {
  getList: (params) => request.get('/team/list', { params }),
  getDetail: (id) => request.get(`/team/detail/${id}`),
  predict: (data) => request.post('/team/predict', data),
  backtest: (data) => request.post('/team/backtest', data),
  getBattleRecord: (params) => request.get('/team/battle/record', { params }),
}

// 系列赛接口
export const seriesApi = {
  getStarList: (params) => request.get('/series/star', { params }),
  getStarDetail: (id) => request.get(`/series/star/${id}`),
  getReview: (params) => request.get('/series/review', { params }),
}

// 预测记录接口
export const recordApi = {
  getList: (params) => request.get('/record/list', { params }),
  getDetail: (id) => request.get(`/record/detail/${id}`),
  calibrate: (params) => request.post('/record/calibrate', null, { params }),
}

// 赔率接口
export const oddsApi = {
  getSource: () => request.get('/datasource/list'),
  evaluate: () => request.post('/datasource/evaluate'),
  switch: (data) => request.post('/datasource/switch', null, { params: data }),
  collect: (data) => request.post('/odds/collect', data),
  backtest: (data) => request.post('/odds/backtest', data),
}

// 数据源接口
export const datasourceApi = {
  getList: () => request.get('/datasource/list'),
  getPage: (params) => request.get('/datasource/page', { params }),
  getDetail: (id) => request.get(`/datasource/detail/${id}`),
  evaluate: () => request.post('/datasource/evaluate'),
  switch: (sourceId) => request.post('/datasource/switch', null, { params: { sourceId } }),
}

// 系统配置接口
export const configApi = {
  get: () => request.get('/config/get'),
  getByGroup: (group) => request.get(`/config/group/${group}`),
  update: (params) => request.post('/config/update', null, { params }),
}

// 赛程接口
export const gameApi = {
  getList: (params) => request.get('/game/list', { params }),
  getDetail: (id) => request.get(`/game/detail/${id}`),
  getRecent: (params) => request.get('/game/recent', { params }),
  getBattle: (params) => request.get('/game/battle', { params }),
}

// 数据接口 (Python 算法层直连)
export const dataApi = {
  update: () => request.post('/data/update'),
  getHistory: (params) => request.get('/data/history', { params }),
  backup: () => request.post('/data/backup'),
  getTeams: (season = '2025-26') => request.get('/data/teams', { params: { season } }),
  getTeamDetail: (id, season = '2025-26') => request.get(`/data/teams/${id}`, { params: { season } }),
  getTeamRoster: (id, season = '2025-26') => request.get(`/data/teams/${id}/roster`, { params: { season } }),
  getPlayers: (params) => request.get('/data/players', { params }),
  getPlayerDetail: (id, season = '2025-26') => request.get(`/data/players/${id}`, { params: { season } }),
  getStandings: (season = '2025-26') => request.get('/data/standings', { params: { season } }),
  getTodayGames: () => request.get('/data/games/today'),
  getUpcomingGames: () => request.get('/data/games/upcoming'),
}
