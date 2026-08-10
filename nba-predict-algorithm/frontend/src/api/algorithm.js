import api from './index'

export const predictTeam = (data) => api.post('/algorithm/team/predict', data)
export const predictPlayer = (data) => api.post('/algorithm/player/predict', data)
export const classifyTeams = (season) => api.get('/algorithm/team/classify', { params: { season } })
export const classifyPlayers = (season) => api.get('/algorithm/player/classify', { params: { season } })
export const getMatchup = (team1Id, team2Id) => api.get(`/algorithm/team/matchup/${team1Id}/${team2Id}`)
export const calculateOdds = (data) => api.post('/algorithm/odds/calculate', data)
export const getSeriesStars = (season, teamId) => api.get('/algorithm/series/star', { params: { season, team_id: teamId } })
