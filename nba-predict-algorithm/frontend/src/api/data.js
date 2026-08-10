import api from './index'

export const getTeams = () => api.get('/data/teams')
export const getTeam = (id) => api.get(`/data/teams/${id}`)
export const getTeamRoster = (id) => api.get(`/data/teams/${id}/roster`)
export const getStandings = () => api.get('/data/standings')
export const getPlayers = (params) => api.get('/data/players', { params })
export const getPlayer = (id) => api.get(`/data/players/${id}`)
export const getTodayGames = (days = 1) => api.get('/data/games/today', { params: { days } })
export const getRecentGames = () => api.get('/data/games/recent')
export const getModelStats = () => api.get('/data/model/stats')
