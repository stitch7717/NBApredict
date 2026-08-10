package com.nba.predict.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.nba.predict.entity.OddsData;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface OddsDataMapper extends BaseMapper<OddsData> {
}
