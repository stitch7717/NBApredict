package com.nba.predict.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.nba.predict.entity.TeamData;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TeamDataMapper extends BaseMapper<TeamData> {
}
