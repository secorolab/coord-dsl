// SPDX-License-Identifier: MPL-2.0
// SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
// Author: Vamsi Kalagaturu
//
// Shared logging for the FSM-coordination examples. Two tagged streams:
//   FSM  (cyan)   - arm controller: the coord2b FSM state each tick
//   BT   (yellow) - BehaviorTree node status transitions (Sequence/Parallel/...)
#ifndef COORD_LOG_HPP
#define COORD_LOG_HPP

#include <behaviortree_cpp/loggers/abstract_logger.h>

#include <chrono>
#include <cstdio>
#include <string>

inline double coord_now_ms()
{
    static const auto start = std::chrono::steady_clock::now();
    return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start)
      .count();
}

inline void log_fsm(const char *who, const std::string &msg)
{
    std::printf("[%8.2f ms] \033[36mFSM\033[0m | %-9s | %s\n", coord_now_ms(), who, msg.c_str());
}

// Prints every BehaviorTree node status transition, so the coordination
// structure (which node runs when) is visible next to the FSM state stream.
class CoordLogger : public BT::StatusChangeLogger
{
  public:
    explicit CoordLogger(BT::TreeNode *root) : BT::StatusChangeLogger(root) {}

    void
      callback(BT::Duration, const BT::TreeNode &node, BT::NodeStatus prev, BT::NodeStatus status)
        override
    {
        std::string label = node.registrationName();
        const auto &ports = node.config().input_ports;
        if (label == "FSMEvent") {
            const auto fsm   = ports.find("fsm");
            const auto event = ports.find("event");
            if (fsm != ports.end() && event != ports.end()) {
                label += " " + fsm->second + "." + event->second;
            }
        }
        std::printf(
          "[%8.2f ms] \033[33mBT \033[0m | %-32s %s -> %s\n",
          coord_now_ms(),
          label.c_str(),
          BT::toStr(prev, true).c_str(),
          BT::toStr(status, true).c_str()
        );
    }

    void flush() override {}
};

#endif // COORD_LOG_HPP
