"""Schema definitions for input data validation."""

from typing import List
from pydantic import BaseModel, Field, field_validator


class StrategyConfig(BaseModel):
    """Strategy configuration loaded from strategy.toml."""

    name: str = Field(..., description="Strategy name")

    # Portfolio construction
    top_k: int = Field(..., gt=0, description="Number of long positions")
    bottom_k: int = Field(default=0, ge=0, description="Number of short positions")
    min_k: int = Field(default=1, ge=1, description="Minimum positions to trade")

    # Capital & execution
    leverage: float = Field(..., gt=0, description="Leverage multiplier")
    lot_size: int = Field(default=100, gt=0, description="Shares per lot")
    cost_bps: float = Field(..., ge=0, description="Transaction cost in basis points")

    # Market filters
    ban_long_markets: List[str] = Field(
        default_factory=list,
        description="Markets to exclude from long positions"
    )
    ban_short_markets: List[str] = Field(
        default_factory=list,
        description="Markets to exclude from short positions"
    )

    @field_validator('top_k', 'min_k')
    @classmethod
    def validate_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Must be at least 1")
        return v

    @field_validator('bottom_k')
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Must be non-negative")
        return v

    @field_validator('leverage')
    @classmethod
    def validate_positive_float(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Leverage must be positive")
        return v

    @field_validator('cost_bps')
    @classmethod
    def validate_cost(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Transaction cost cannot be negative")
        return v
