rm(list = ls())
cat("\14")

library("dplyr")
# install.packages("dplyr")
library("ggplot2")
# install.packages("ggplot2")

# setwd("R:\\Projects\\CAS\\Mitigation Impact 2024\\data")
setwd("R:\\Projects\\CAS\\Mitigation Impact 2024\\output v5")
getwd()

#### Set Scenario
mat.parameters <- matrix(NA, nrow = 6, ncol = 4)
#delta.coi.on.rrv
mat.parameters[1,] <- 0.5
#delta.acoi.on.rrv
mat.parameters[2,] <- rep(c(0.5, -0.4), each=2)
#riskeffect.rrv
mat.parameters[3,] <- 2
#riskeffect.coi
mat.parameters[4,] <- rep(c(1, 1.5))
#riskeffect.acoi
mat.parameters[5,] <- rep(c(1, 1.5))
#riskeffect.vi
mat.parameters[6,] <- 1.25

write.csv(mat.parameters, "scenario parameters.csv")

for (i in 1:4) {
{
case.fname.prefix <- paste("Case", 200+i, sep=" ")
N <- 1500000
pct.coi <- 0.25
pct.acoi <- 0.25
pct.rrv <- 0.5
delta.coi.on.rrv <- mat.parameters[1,i]
delta.acoi.on.rrv <- mat.parameters[2,i]

pct.vi <- 0.25
delta.coi.on.vi <- 0.25
delta.acoi.on.vi <- 0.25

prob.base <- 0.05
riskeffect.var.rrv <- mat.parameters[3,i]
riskeffect.var.rrv.cap <- 1.5
riskeffect.coi <- mat.parameters[4,i]
riskeffect.acoi <- mat.parameters[5,i]
riskeffect.V1 <- mat.parameters[6,i]
riskeffect.V2 <- mat.parameters[6,i]
riskeffect.V3 <- mat.parameters[6,i]
riskeffect.V4 <- mat.parameters[6,i]
riskeffect.V5 <- mat.parameters[6,i]
riskeffect.V6 <- mat.parameters[6,i]
riskeffect.V7 <- mat.parameters[6,i]
riskeffect.V8 <- mat.parameters[6,i]
riskeffect.V9 <- mat.parameters[6,i]
riskeffect.V10 <- mat.parameters[6,i]
claim.loss <- 10000
}

df.parameters <- t(data.frame(
  case.fname.prefix,
  N,
  pct.coi,
  pct.acoi,
  pct.rrv,
  delta.coi.on.rrv,
  delta.acoi.on.rrv,
  pct.vi,
  delta.coi.on.vi,
  delta.acoi.on.vi,
  prob.base,
  riskeffect.coi,
  riskeffect.acoi,
  riskeffect.var.rrv,
  riskeffect.var.rrv.cap,
  riskeffect.V1,
  riskeffect.V2,
  riskeffect.V3,
  riskeffect.V4,
  riskeffect.V5,
  riskeffect.V6,
  riskeffect.V7,
  riskeffect.V8,
  riskeffect.V9,
  riskeffect.V10,
  claim.loss
))
colnames(df.parameters) <- c("value")
df.parameters
write.csv(df.parameters,
          paste(case.fname.prefix, "parameters.csv", sep=" "))

set.seed(12345)

build_variable <- function(var.draw, var.cutoff) {
  rowcnt <- length(var.draw)
  n <- 1:rowcnt
  df <- data.frame(var.draw, n) %>% 
    mutate(row=1) %>% 
    arrange(var.draw) %>% 
    mutate(var.draw = cumsum(row)/rowcnt) %>% 
    mutate(var.out=ifelse(var.draw < var.cutoff, 1, 0)) %>% 
    arrange(n)
  return(df$var.out)
}

# Build main class of interest (coi) and additional class of interest (acoi)
tmp.draw <- runif(n=N, min=0, max=1)
var.coi <- build_variable(var.draw = tmp.draw, var.cutoff = pct.coi)

tmp.draw <- runif(n=N, min=0, max=1)
var.acoi <- build_variable(var.draw = tmp.draw, var.cutoff = pct.acoi)

# Build regulated rating variable (rrv)
tmp.denom <- (1 + delta.coi.on.rrv * var.coi) *
  (1 + delta.acoi.on.rrv * var.acoi)
tmp.draw <- runif(n=N, min=0, max=1) / tmp.denom
var.rrv <- build_variable(var.draw = tmp.draw, var.cutoff = pct.rrv)

df0 <- data.frame(var.coi, var.acoi, var.rrv)
df0.summ <- df0 %>% 
  group_by(var.coi, var.acoi, var.rrv) %>% 
  summarise(reccnt = n())

write.csv(cor(df0),
          paste(case.fname.prefix, "Key Var and Class Correlations.csv", sep=" "))
write.csv(df0.summ,
          paste(case.fname.prefix, "Key Var and Class Record Counts.csv", sep=" "),
          row.names=FALSE)

{
tmp.denom <- (1 + delta.coi.on.vi * var.coi) *
  (1 + delta.acoi.on.vi * var.acoi)

tmp.draw <- runif(n=N, min=0, max=1) / tmp.denom
V1 <- build_variable(var.draw = tmp.draw, var.cutoff = pct.vi)
tmp.draw <- runif(n=N, min=0, max=1) / tmp.denom
V2 <- build_variable(var.draw = tmp.draw, var.cutoff = pct.vi)
tmp.draw <- runif(n=N, min=0, max=1) / tmp.denom
V3 <- build_variable(var.draw = tmp.draw, var.cutoff = pct.vi)
tmp.draw <- runif(n=N, min=0, max=1) / tmp.denom
V4 <- build_variable(var.draw = tmp.draw, var.cutoff = pct.vi)
tmp.draw <- runif(n=N, min=0, max=1) / tmp.denom
V5 <- build_variable(var.draw = tmp.draw, var.cutoff = pct.vi)
tmp.draw <- runif(n=N, min=0, max=1) / tmp.denom
V6 <- build_variable(var.draw = tmp.draw, var.cutoff = pct.vi)
tmp.draw <- runif(n=N, min=0, max=1) / tmp.denom
V7 <- build_variable(var.draw = tmp.draw, var.cutoff = pct.vi)
tmp.draw <- runif(n=N, min=0, max=1) / tmp.denom
V8 <- build_variable(var.draw = tmp.draw, var.cutoff = pct.vi)
tmp.draw <- runif(n=N, min=0, max=1) / tmp.denom
V9 <- build_variable(var.draw = tmp.draw, var.cutoff = pct.vi)
tmp.draw <- runif(n=N, min=0, max=1) / tmp.denom
V10 <- build_variable(var.draw = tmp.draw, var.cutoff = pct.vi)
}
{
R.rrv <- lm(var.rrv ~ var.coi)$residuals
R1 <- lm(V1 ~ var.coi)$residuals
R2 <- lm(V2 ~ var.coi)$residuals
R3 <- lm(V3 ~ var.coi)$residuals
R4 <- lm(V4 ~ var.coi)$residuals
R5 <- lm(V5 ~ var.coi)$residuals
R6 <- lm(V6 ~ var.coi)$residuals
R7 <- lm(V7 ~ var.coi)$residuals
R8 <- lm(V8 ~ var.coi)$residuals
R9 <- lm(V9 ~ var.coi)$residuals
R10 <- lm(V10 ~ var.coi)$residuals
}

var.df <- data.frame(V1, V2, V3, V4, V5, V6, V7, V8, V9, V10)
R.df <- data.frame(R.rrv, R1, R2, R3, R4, R5, R6, R7, R8, R9, R10)

# join variables into data frame
df <- data.frame(df0, var.df, R.df)
write.csv(cor(df), paste(case.fname.prefix,
                         "Full Correlation Matrix.csv",
                         sep=" "))

# set probabilities
df2 <- df %>% 
  mutate(prob = prob.base*(1+var.coi*(riskeffect.coi-1))*
           (1+var.acoi*(riskeffect.acoi-1))*
           (1+var.rrv*(riskeffect.var.rrv-1))*
           (1+V1*(riskeffect.V1-1))*
           (1+V2*(riskeffect.V2-1))*
           (1+V3*(riskeffect.V3-1))*
           (1+V4*(riskeffect.V4-1))*
           (1+V5*(riskeffect.V5-1))*
           (1+V6*(riskeffect.V6-1))*
           (1+V7*(riskeffect.V7-1))*
           (1+V8*(riskeffect.V8-1))*
           (1+V9*(riskeffect.V9-1))*
           (1+V10*(riskeffect.V10-1)))
df2$prob <- df2$prob * (prob.base/mean(df2$prob))
df2$var.rrv.cap <- riskeffect.var.rrv.cap * var.rrv + 1 * (1 - var.rrv)

summary(df2)

df2$act <- rpois(n=N, lambda=df2$prob)
df2$act.loss <- df2$act * claim.loss

df2.var.rrv.0 <- df2[var.rrv==0,]
df2.var.rrv.1 <- df2[var.rrv==1,]
df2.var.rrv.0$company <- sample(seq(1, 3),
                                size = nrow(df2.var.rrv.0),
                                replace = TRUE,
                                prob = c(1/6, 2/6, 3/6))
df2.var.rrv.1$company <- sample(seq(1, 3),
                                   size = nrow(df2.var.rrv.1),
                                   replace = TRUE,
                                   prob = c(3/6, 2/6, 1/6))

df2 <- rbind(df2.var.rrv.0, df2.var.rrv.1)

{
#### Run Company 1 ####
{
df2.company <- df2[df2$company==1,]
company.fname.prefix <- "Comp 1"
{
#### Unrestricted Model ####
m.glm.KV <- glm(act ~ var.rrv +
                V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
                data=df2.company, family=poisson(link="log"))

#### Capped RRV Model ####
m.glm.V_offset <- glm(act ~ offset(log(var.rrv.cap)) +
                      V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
                      data=df2.company, family=poisson(link="log"))

### Prohibit Variable Model ####
m.glm.V <- glm(act ~ 
               V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
               data=df2.company, family=poisson(link="log"))

#### Control Variable Test Model ####
m.glm.KC1V <- glm(act ~ var.rrv + var.coi +
                     V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
                   data=df2.company, family=poisson(link="log"))

#### Residual Variable Model ####
{
  lm.rrv <- lm(var.rrv ~ var.coi, data=df2.company)
  lm.1 <- lm(V1 ~ var.coi, data=df2.company)
  lm.2 <- lm(V2 ~ var.coi, data=df2.company)
  lm.3 <- lm(V3 ~ var.coi, data=df2.company)
  lm.4 <- lm(V4 ~ var.coi, data=df2.company)
  lm.5 <- lm(V5 ~ var.coi, data=df2.company)
  lm.6 <- lm(V6 ~ var.coi, data=df2.company)
  lm.7 <- lm(V7 ~ var.coi, data=df2.company)
  lm.8 <- lm(V8 ~ var.coi, data=df2.company)
  lm.9 <- lm(V9 ~ var.coi, data=df2.company)
  lm.10 <- lm(V10 ~ var.coi, data=df2.company)
  df2.company$R1.rrv <- df2.company$var.rrv - predict(lm.rrv, df2.company, type="response")
  df2.company$R1.1 <- df2.company$V1 - predict(lm.1, df2.company, type="response")
  df2.company$R1.2 <- df2.company$V2 - predict(lm.2, df2.company, type="response")
  df2.company$R1.3 <- df2.company$V3 - predict(lm.3, df2.company, type="response")
  df2.company$R1.4 <- df2.company$V4 - predict(lm.4, df2.company, type="response")
  df2.company$R1.5 <- df2.company$V5 - predict(lm.5, df2.company, type="response")
  df2.company$R1.6 <- df2.company$V6 - predict(lm.6, df2.company, type="response")
  df2.company$R1.7 <- df2.company$V7 - predict(lm.7, df2.company, type="response")
  df2.company$R1.8 <- df2.company$V8 - predict(lm.8, df2.company, type="response")
  df2.company$R1.9 <- df2.company$V9 - predict(lm.9, df2.company, type="response")
  df2.company$R1.10 <- df2.company$V10 - predict(lm.10, df2.company, type="response")
}
m.glm.KRglobal <- glm(act ~ R.rrv +
                      R1 + R2 + R3 + R4 + R5 + R6 + R7 + R8 + R9 + R10,
                      data=df2.company, family=poisson(link="log"))
m.glm.KR <- glm(act ~ R1.rrv +
                R1.1 + R1.2 + R1.3 + R1.4 + R1.5 + R1.6 + R1.7 + R1.8 + R1.9 + R1.10,
                data=df2.company, family=poisson(link="log"))

write.csv(m.glm.KV$coefficients, 
          paste(case.fname.prefix,
                company.fname.prefix,
                "classic GLM.csv",sep=" "))
write.csv(m.glm.V_offset$coefficients, 
          paste(case.fname.prefix,
                company.fname.prefix,
                "capped GLM.csv",sep=" "))
write.csv(m.glm.V$coefficients, 
          paste(case.fname.prefix,
                company.fname.prefix,
                "prohibited GLM.csv",sep=" "))
write.csv(m.glm.KC1V$coefficients, 
          paste(case.fname.prefix,
                company.fname.prefix,
                "control variable GLM.csv",sep=" "))
write.csv(m.glm.KRglobal$coefficients, 
          paste(case.fname.prefix,
                company.fname.prefix,
                "global residualized GLM.csv",sep=" "))
write.csv(m.glm.KR$coefficients, 
          paste(case.fname.prefix,
                company.fname.prefix,
                "residualized GLM.csv",sep=" "))

}

{
df2.company$pred.KV <- predict(m.glm.KV, df2.company, type="response")
df2.company$pred.V_offset <- predict(m.glm.V_offset, df2.company, type="response")
df2.company$pred.V <- predict(m.glm.V, df2.company, type="response")
df2.company$pred.KC1V <- predict(m.glm.KC1V, df2.company, type="response")
df2.company$pred.KRglobal <- predict(m.glm.KRglobal, df2.company, type="response")
df2.company$pred.KR <- predict(m.glm.KR, df2.company, type="response")
}

C1_factor <- exp(df2.company$var.coi * m.glm.KC1V$coefficients[3])
tmp.pred.adj <- df2.company$pred.KC1V / C1_factor
tmp.pred.tot <- sum(tmp.pred.adj)
tmp.pred.act.tot <- sum(df2.company$act)
df2.company$pred.KC1V_exC1 <- tmp.pred.adj * tmp.pred.act.tot / tmp.pred.tot

df3.company <- df2.company %>% 
  mutate(true.loss = prob * claim.loss,
         pred.loss.KV = pred.KV * claim.loss,
         pred.loss.V_offset = pred.V_offset * claim.loss,
         pred.loss.V = pred.V * claim.loss,
         pred.loss.KC1V = pred.KC1V * claim.loss,
         pred.loss.KC1V_exC1 = pred.KC1V_exC1 * claim.loss,
         pred.loss.KRglobal = pred.KRglobal * claim.loss,
         pred.loss.KR = pred.KR * claim.loss)

df3.summ <- df3.company %>% 
  group_by(var.coi, var.acoi, var.rrv) %>% 
  summarise(reccnt = n(),
            true.loss = sum(true.loss),
            act.loss = sum(act.loss),
            pred.loss.KV = sum(pred.loss.KV),
            pred.loss.V_offset = sum(pred.loss.V_offset),
            pred.loss.V = sum(pred.loss.V),
            pred.loss.KC1V = sum(pred.loss.KC1V),
            pred.loss.KC1V_exC1 = sum(pred.loss.KC1V_exC1),
            pred.loss.KRglobal = sum(pred.loss.KRglobal),
            pred.loss.KR = sum(pred.loss.KR))

df3.summ
write.csv(df3.summ,
          paste(case.fname.prefix,
              company.fname.prefix,
              "Model Summary Data.csv", sep = " "),
          row.names=FALSE)
}

  #### Run Company 2 ####
  {
    df2.company <- df2[df2$company==2,]
    company.fname.prefix <- "Comp 2"
    {
      #### Classic Model ####
      m.glm.KV <- glm(act ~ var.rrv +
                        V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
                      data=df2.company, family=poisson(link="log"))
      
      #### Capped Key Var Model ####
      m.glm.V_offset <- glm(act ~ offset(log(var.rrv.cap)) +
                              V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
                            data=df2.company, family=poisson(link="log"))
      
      ### Prohibit Variable Model ####
      m.glm.V <- glm(act ~ 
                       V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
                     data=df2.company, family=poisson(link="log"))
      
      #### Control Variable Test Model ####
      m.glm.KC1V <- glm(act ~ var.rrv + var.coi +
                          V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
                        data=df2.company, family=poisson(link="log"))
      
      #### Residual Variable Model ####
      {
        lm.rrv <- lm(var.rrv ~ var.coi, data=df2.company)
        lm.1 <- lm(V1 ~ var.coi, data=df2.company)
        lm.2 <- lm(V2 ~ var.coi, data=df2.company)
        lm.3 <- lm(V3 ~ var.coi, data=df2.company)
        lm.4 <- lm(V4 ~ var.coi, data=df2.company)
        lm.5 <- lm(V5 ~ var.coi, data=df2.company)
        lm.6 <- lm(V6 ~ var.coi, data=df2.company)
        lm.7 <- lm(V7 ~ var.coi, data=df2.company)
        lm.8 <- lm(V8 ~ var.coi, data=df2.company)
        lm.9 <- lm(V9 ~ var.coi, data=df2.company)
        lm.10 <- lm(V10 ~ var.coi, data=df2.company)
        df2.company$R2.rrv <- df2.company$var.rrv - predict(lm.rrv, df2.company, type="response")
        df2.company$R2.1 <- df2.company$V1 - predict(lm.1, df2.company, type="response")
        df2.company$R2.2 <- df2.company$V2 - predict(lm.2, df2.company, type="response")
        df2.company$R2.3 <- df2.company$V3 - predict(lm.3, df2.company, type="response")
        df2.company$R2.4 <- df2.company$V4 - predict(lm.4, df2.company, type="response")
        df2.company$R2.5 <- df2.company$V5 - predict(lm.5, df2.company, type="response")
        df2.company$R2.6 <- df2.company$V6 - predict(lm.6, df2.company, type="response")
        df2.company$R2.7 <- df2.company$V7 - predict(lm.7, df2.company, type="response")
        df2.company$R2.8 <- df2.company$V8 - predict(lm.8, df2.company, type="response")
        df2.company$R2.9 <- df2.company$V9 - predict(lm.9, df2.company, type="response")
        df2.company$R2.10 <- df2.company$V10 - predict(lm.10, df2.company, type="response")
      }
      m.glm.KRglobal <- glm(act ~ R.rrv +
                               R1 + R2 + R3 + R4 + R5 + R6 + R7 + R8 + R9 + R10,
                             data=df2.company, family=poisson(link="log"))
      m.glm.KR <- glm(act ~ R2.rrv +
                        R2.1 + R2.2 + R2.3 + R2.4 + R2.5 + R2.6 + R2.7 + R2.8 + R2.9 + R2.10,
                      data=df2.company, family=poisson(link="log"))

      write.csv(m.glm.KV$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "classic GLM.csv",sep=" "))
      write.csv(m.glm.V_offset$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "capped GLM.csv",sep=" "))
      write.csv(m.glm.V$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "prohibited GLM.csv",sep=" "))
      write.csv(m.glm.KC1V$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "control variable GLM.csv",sep=" "))
      write.csv(m.glm.KRglobal$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "global residualized GLM.csv",sep=" "))
      write.csv(m.glm.KR$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "residualized GLM.csv",sep=" "))

    }
    
    {
      df2.company$pred.KV <- predict(m.glm.KV, df2.company, type="response")
      df2.company$pred.V_offset <- predict(m.glm.V_offset, df2.company, type="response")
      df2.company$pred.V <- predict(m.glm.V, df2.company, type="response")
      df2.company$pred.KC1V <- predict(m.glm.KC1V, df2.company, type="response")
      df2.company$pred.KRglobal <- predict(m.glm.KRglobal, df2.company, type="response")
      df2.company$pred.KR <- predict(m.glm.KR, df2.company, type="response")
    }
    
    C1_factor <- exp(df2.company$var.coi * m.glm.KC1V$coefficients[3])
    tmp.pred.adj <- df2.company$pred.KC1V / C1_factor
    tmp.pred.tot <- sum(tmp.pred.adj)
    tmp.pred.act.tot <- sum(df2.company$act)
    df2.company$pred.KC1V_exC1 <- tmp.pred.adj * tmp.pred.act.tot / tmp.pred.tot
    
    df3.company <- df2.company %>% 
      mutate(true.loss = prob * claim.loss,
             pred.loss.KV = pred.KV * claim.loss,
             pred.loss.V_offset = pred.V_offset * claim.loss,
             pred.loss.V = pred.V * claim.loss,
             pred.loss.KC1V = pred.KC1V * claim.loss,
             pred.loss.KC1V_exC1 = pred.KC1V_exC1 * claim.loss,
             pred.loss.KRglobal = pred.KRglobal * claim.loss,
             pred.loss.KR = pred.KR * claim.loss)
    
    df3.summ <- df3.company %>% 
      group_by(var.coi, var.acoi, var.rrv) %>% 
      summarise(reccnt = n(),
                true.loss = sum(true.loss),
                act.loss = sum(act.loss),
                pred.loss.KV = sum(pred.loss.KV),
                pred.loss.V_offset = sum(pred.loss.V_offset),
                pred.loss.V = sum(pred.loss.V),
                pred.loss.KC1V = sum(pred.loss.KC1V),
                pred.loss.KC1V_exC1 = sum(pred.loss.KC1V_exC1),
                pred.loss.KRglobal = sum(pred.loss.KRglobal),
                pred.loss.KR = sum(pred.loss.KR))
    
    df3.summ
    write.csv(df3.summ,
              paste(case.fname.prefix,
                    company.fname.prefix,
                    "Model Summary Data.csv", sep = " "),
              row.names=FALSE)
  }

  #### Run Company 3 ####
  {
    df2.company <- df2[df2$company==3,]
    company.fname.prefix <- "Comp 3"
    {
      #### Classic Model ####
      m.glm.KV <- glm(act ~ var.rrv +
                        V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
                      data=df2.company, family=poisson(link="log"))
      
      #### Capped Key Var Model ####
      m.glm.V_offset <- glm(act ~ offset(log(var.rrv.cap)) +
                              V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
                            data=df2.company, family=poisson(link="log"))
      
      ### Prohibit Variable Model ####
      m.glm.V <- glm(act ~ 
                       V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
                     data=df2.company, family=poisson(link="log"))
      
      #### Control Variable Test Model ####
      m.glm.KC1V <- glm(act ~ var.rrv + var.coi +
                          V1 + V2 + V3 + V4 + V5 + V6 + V7 + V8 + V9 + V10,
                        data=df2.company, family=poisson(link="log"))
      
      #### Residual Variable Model ####
      {
        lm.rrv <- lm(var.rrv ~ var.coi, data=df2.company)
        lm.1 <- lm(V1 ~ var.coi, data=df2.company)
        lm.2 <- lm(V2 ~ var.coi, data=df2.company)
        lm.3 <- lm(V3 ~ var.coi, data=df2.company)
        lm.4 <- lm(V4 ~ var.coi, data=df2.company)
        lm.5 <- lm(V5 ~ var.coi, data=df2.company)
        lm.6 <- lm(V6 ~ var.coi, data=df2.company)
        lm.7 <- lm(V7 ~ var.coi, data=df2.company)
        lm.8 <- lm(V8 ~ var.coi, data=df2.company)
        lm.9 <- lm(V9 ~ var.coi, data=df2.company)
        lm.10 <- lm(V10 ~ var.coi, data=df2.company)
        df2.company$R3.rrv <- df2.company$var.rrv - predict(lm.rrv, df2.company, type="response")
        df2.company$R3.1 <- df2.company$V1 - predict(lm.1, df2.company, type="response")
        df2.company$R3.2 <- df2.company$V2 - predict(lm.2, df2.company, type="response")
        df2.company$R3.3 <- df2.company$V3 - predict(lm.3, df2.company, type="response")
        df2.company$R3.4 <- df2.company$V4 - predict(lm.4, df2.company, type="response")
        df2.company$R3.5 <- df2.company$V5 - predict(lm.5, df2.company, type="response")
        df2.company$R3.6 <- df2.company$V6 - predict(lm.6, df2.company, type="response")
        df2.company$R3.7 <- df2.company$V7 - predict(lm.7, df2.company, type="response")
        df2.company$R3.8 <- df2.company$V8 - predict(lm.8, df2.company, type="response")
        df2.company$R3.9 <- df2.company$V9 - predict(lm.9, df2.company, type="response")
        df2.company$R3.10 <- df2.company$V10 - predict(lm.10, df2.company, type="response")
      }
      m.glm.KRglobal <- glm(act ~ R.rrv +
                               R1 + R2 + R3 + R4 + R5 + R6 + R7 + R8 + R9 + R10,
                             data=df2.company, family=poisson(link="log"))
      m.glm.KR <- glm(act ~ R3.rrv +
                        R3.1 + R3.2 + R3.3 + R3.4 + R3.5 + R3.6 + R3.7 + R3.8 + R3.9 + R3.10,
                      data=df2.company, family=poisson(link="log"))
      
      write.csv(m.glm.KV$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "classic GLM.csv",sep=" "))
      write.csv(m.glm.V_offset$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "capped GLM.csv",sep=" "))
      write.csv(m.glm.V$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "prohibited GLM.csv",sep=" "))
      write.csv(m.glm.KC1V$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "control variable GLM.csv",sep=" "))
      write.csv(m.glm.KRglobal$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "global residualized GLM.csv",sep=" "))
      write.csv(m.glm.KR$coefficients, 
                paste(case.fname.prefix,
                      company.fname.prefix,
                      "residualized GLM.csv",sep=" "))

    }
    
    {
      df2.company$pred.KV <- predict(m.glm.KV, df2.company, type="response")
      df2.company$pred.V_offset <- predict(m.glm.V_offset, df2.company, type="response")
      df2.company$pred.V <- predict(m.glm.V, df2.company, type="response")
      df2.company$pred.KC1V <- predict(m.glm.KC1V, df2.company, type="response")
      df2.company$pred.KRglobal <- predict(m.glm.KRglobal, df2.company, type="response")
      df2.company$pred.KR <- predict(m.glm.KR, df2.company, type="response")
    }

C1_factor <- exp(df2.company$var.coi * m.glm.KC1V$coefficients[3])
tmp.pred.adj <- df2.company$pred.KC1V / C1_factor
tmp.pred.tot <- sum(tmp.pred.adj)
tmp.pred.act.tot <- sum(df2.company$act)
df2.company$pred.KC1V_exC1 <- tmp.pred.adj * tmp.pred.act.tot / tmp.pred.tot
    
      df3.company <- df2.company %>% 
      mutate(true.loss = prob * claim.loss,
             pred.loss.KV = pred.KV * claim.loss,
             pred.loss.V_offset = pred.V_offset * claim.loss,
             pred.loss.V = pred.V * claim.loss,
             pred.loss.KC1V = pred.KC1V * claim.loss,
             pred.loss.KC1V_exC1 = pred.KC1V_exC1 * claim.loss,
             pred.loss.KRglobal = pred.KRglobal * claim.loss,
             pred.loss.KR = pred.KR * claim.loss)
    
    df3.summ <- df3.company %>% 
      group_by(var.coi, var.acoi, var.rrv) %>% 
      summarise(reccnt = n(),
                true.loss = sum(true.loss),
                act.loss = sum(act.loss),
                pred.loss.KV = sum(pred.loss.KV),
                pred.loss.V_offset = sum(pred.loss.V_offset),
                pred.loss.V = sum(pred.loss.V),
                pred.loss.KC1V = sum(pred.loss.KC1V),
                pred.loss.KC1V_exC1 = sum(pred.loss.KC1V_exC1),
                pred.loss.KRglobal = sum(pred.loss.KRglobal),
                pred.loss.KR = sum(pred.loss.KR))
    
    df3.summ
    write.csv(df3.summ,
              paste(case.fname.prefix,
                    company.fname.prefix,
                    "Model Summary Data.csv", sep = " "),
              row.names=FALSE)
  }
}
}
