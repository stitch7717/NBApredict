package com.nba.predict.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.Player;

public interface PlayerService {

    /**
     * 分页查询球员列表
     */
    Page<Player> listPlayers(int page, int size, String keyword, String position, Integer teamId);

    /**
     * 获取球员详情
     */
    Player getPlayerDetail(Long playerId);

    /**
     * 球员预测
     */
    Object predict(Long playerId, Long opponentPlayerId, String scene, String homeAway);
}
