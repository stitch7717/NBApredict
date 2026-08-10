package com.nba.predict.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.nba.predict.entity.PlayerData;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface PlayerDataMapper extends BaseMapper<PlayerData> {
}
