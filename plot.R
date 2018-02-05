#!/usr/bin/env Rscript

library(ggplot2)
library(egg)

plot.cc <- function(data, name) {
    data <- transform(data, time=(time-time[1])/3600)
    plot <- ggplot(data, aes(x=time, y=voltage)) + geom_line() +
        labs(x="time / h", y="voltage / V") +
        scale_y_continuous(limits=c(0.8, 1.6))
    ggsave(name, plot, width=1200/300, height=1200/300, units="in")
}

plot.cw <- function(data, name) {
    data <- transform(data, time=(time-time[1])/3600)

    p.v <- ggplot(data, aes(x=time, y=voltage)) + geom_line() +
        theme(axis.text.x = element_blank(),
              axis.title.x = element_blank(),
              axis.ticks.x = element_blank()) +
        scale_y_continuous(limits=c(0.8, 1.6)) +
        scale_x_continuous(limits=c(0, max(data$time))) +
        ylab("voltage / V")
    p.i <- ggplot(subset(data, current > 0), aes(x=time, y=current*1000)) + geom_line() +
        scale_x_continuous(limits=c(0, max(data$time))) +
        ylab("current / mA") +
        xlab("time / h")

    plot <- ggarrange(p.v, p.i, ncol=1, heights=c(1, 0.5))
    ggsave(name, plot, width=1200/300, height=1200/300*1.5, units="in")
}

args <- commandArgs(trailingOnly=TRUE)
name <- paste(args[1], ".png", sep="")

data <- read.csv(args[1], header=TRUE)
if ("capacity" %in% names(data)) {
    plot <- plot.cc(data, name)
} else {
    plot <- plot.cw(data, name)
}
