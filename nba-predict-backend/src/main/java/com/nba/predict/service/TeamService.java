package com.nba.predict.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.Team;

public interface TeamService {

    /**
     * 分页查询球队列表
     */
    Page<Team> listTeams(int page, int size, String conference, String defenseType, String offenseType);

    /**
     * 获取球队详情
     */
    Team getTeamDetail(Long teamId);

    /**
     * 球队对战预测
     */
    Object predict(Long homeTeamId, Long awayTeamId, String scene, boolean useOdds);
}
