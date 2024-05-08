from pixiu.builder.helper import CodeWriter


# indicator
class IndicatorModule:

    def __init__(self,):
        pass

    def generate_code(self, function_name, options, params_list):
        cw = CodeWriter()
        return cw.generate_code(function_name, options, params_list)

    def adx(self, options):
        """ Average Directional Movement Index (Momentum Indicators)"""
        code = self.generate_code("iADX", options, ("symbol_data",
                                                    {"name": "period", "val_name": "timeperiod"},
                                                    "shift"))
        return code

    def ma(self, options):
        """Calculates the Moving Average indicator and returns its value."""
        code = self.generate_code("iMA", options, (
            {"name": "price_data", "val_name": "price_data"},
            {"name": "period", "val_name": "timeperiod"}, "shift", "matype"))
        return code

    def ad(self, options):
        """Chaikin A/D Line (Volume Indicators)"""
        code = self.generate_code("iAD", options, ("symbol_data", "shift"))
        return code

    def atr(self, options):
        """Average True Range (Volatility Indicators)"""
        code = self.generate_code("iATR", options, ("symbol_data",
                                                    {"name": "period", "val_name": "timeperiod"},
                                                    "shift"))
        return code

    def bands(self, options):
        """Bollinger Bands (Overlap Studies)"""
        code = self.generate_code("iBands", options, ("symbol_data",
                                                    {"name": "period", "val_name": "timeperiod"},
                                                    {"name": "stddev_up", "val_name": "nbdevup"},
                                                    {"name": "stddev_down", "val_name": "nbdevdn"},
                                                    "matype",
                                                    "shift"))
        return code

    def cci(self, options):
        """Commodity Channel Index (Momentum Indicators)"""
        code = self.generate_code("iCCI", options, ("symbol_data",
                                                    {"name": "period", "val_name": "timeperiod"},
                                                    "shift"))
        return code

    def chaikin(self, options):
        """Chaikin A/D Oscillator (Volume Indicators)"""
        code = self.generate_code("iChaikin", options, ("symbol_data",
                                                    {"name": "fast", "val_name": "fastperiod"},
                                                    {"name": "slow", "val_name": "slowperiod"},
                                                    "shift"))
        return code

    def dema(self, options):
        """Double Exponential Moving Average (Overlap Studies)"""
        code = self.generate_code("iDEMA", options, ("symbol_data",
                                                    {"name": "period", "val_name": "timeperiod"},
                                                    "shift"))
        return code

    def momentum(self, options):
        """ Momentum (Momentum Indicators)"""
        code = self.generate_code("iMomentum", options, ("symbol_data",
                                                    {"name": "period", "val_name": "timeperiod"},
                                                    "shift"))
        return code

    def mfi(self, options):
        """Money Flow Index (Momentum Indicators)"""
        code = self.generate_code("iMFI", options, ("symbol_data",
                                                    {"name": "period", "val_name": "timeperiod"},
                                                    "shift"))
        return code

    def macd(self, options):
        """Moving Average Convergence/Divergence (Momentum Indicators)"""
        code = self.generate_code("iMACD", options, ("symbol_data",
                                                    {"name": "fast", "val_name": "fastperiod"},
                                                    {"name": "slow", "val_name": "slowperiod"},
                                                    {"name": "signal", "val_name": "signalperiod"},
                                                    "shift"))
        return code

    def obv(self, options):
        """On Balance Volume (Volume Indicators)"""
        code = self.generate_code("iOBV", options, ("symbol_data",
                                                    "shift"))
        return code

    def sar(self, options):
        """ Parabolic SAR (Overlap Studies)"""
        code = self.generate_code("iSAR", options, ("symbol_data",
                                                    {"name": "acc", "val_name": "acceleration"},
                                                    {"name": "max", "val_name": "maximum"},
                                                    "shift"))
        return code

    def rsi(self, options):
        """Relative Strength Index (Momentum Indicators)"""
        code = self.generate_code("iRSI", options, ("symbol_data",
                                                    {"name": "period", "val_name": "timeperiod"},
                                                    "shift"))
        return code

    def stddev(self, options):
        """Standard Deviation (Statistic Functions)"""
        code = self.generate_code("iStdDev", options, ("symbol_data",
                                                    {"name": "period", "val_name": "timeperiod"},
                                                    {"name": "stddev", "val_name": "nbdev"},
                                                    "shift"))
        return code

    def stochastic(self, options):
        """Stochastic (Momentum Indicators)"""
        code = self.generate_code("iStochastic", options, ("symbol_data",
                                                    {"name": "fastk", "val_name": "fastk_period"},
                                                    {"name": "slowk", "val_name": "slowk_period"},
                                                    {"name": "slowk_matype", "val_name": "slowk_matype"},
                                                    {"name": "slowd", "val_name": "slowd_period"},
                                                    {"name": "slowd_matype", "val_name": "slowd_matype"},
                                                    "shift"))
        return code

    def tema(self, options):
        """Triple Exponential Moving Average (Overlap Studies)"""
        code = self.generate_code("iTEMA", options, ({"name": "price_data", "val_name": "price_data"},
                                                    {"name": "period", "val_name": "timeperiod"},
                                                    "shift"))
        return code

    def wpr(self, options):
        """Williams' %R (Momentum Indicators)"""
        code = self.generate_code("iWPR", options, ("symbol_data",
                                                    {"name": "period", "val_name": "timeperiod"},
                                                    "shift"))
        return code

